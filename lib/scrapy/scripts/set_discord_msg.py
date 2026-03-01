import argparse
import enum
import os
import subprocess
import time

from .. import scrapy_util

GITHUB_ENV_FILE = os.getenv('GITHUB_ENV')

RUN_NUMBER = os.getenv('GITHUB_RUN_NUMBER')
SERVER_URL = os.getenv('GITHUB_SERVER_URL')
REPO_NAME = os.getenv('GITHUB_REPOSITORY')
RUN_ID = os.getenv('GITHUB_RUN_ID')
RUN_EVENT = os.getenv('GITHUB_EVENT_NAME')

RUN_URL = f"{SERVER_URL}/{REPO_NAME}/actions/runs/{RUN_ID}"
REPO_URL = f"{SERVER_URL}/{REPO_NAME}"

START_TS = os.getenv('START_TS')
JOB_DISPLAY_NAMES = {
    'dcg_wiki': 'DCG Wiki',
    'dcg_main': 'DCG Main',
    'tcg_plus': 'TCG+',
}


def main():

  parser = argparse.ArgumentParser()
  parser.add_argument('--job',
                      choices=JOB_DISPLAY_NAMES.keys(),
                      required=True,
                      help='Job identifier for Discord messaging context.')

  group = parser.add_mutually_exclusive_group(required=True)
  group.add_argument('--start',
                     action='store_true',
                     help='Set the start message for the job.')
  group.add_argument(
      '--end',
      action='store_true',
      help='Set the end (success/failure/cancel) message for the job.')
  parser.add_argument('--commit-hash', type=str, nargs='?', default=None)
  args = parser.parse_args()

  if args.start:
    JobState.START.write_env_var(args.job)
  elif args.end:
    JobState.SUCCEEDED.write_env_var(args.job, success_commit=args.commit_hash)
    JobState.FAILED.write_env_var(args.job)
    JobState.CANCELED.write_env_var(args.job)
  else:
    parser.error("One of --start or --end must be provided")


class JobState(enum.Enum):
  START = 'start'
  SUCCEEDED = 'succeeded'
  FAILED = 'failed'
  CANCELED = 'canceled'

  def title(self, job_key: str, success_commit: str | None = None) -> str:
    try:
      status_emoji = JOB_STATE_STATUS_EMOJI[self]
      past_tense = JOB_STATE_PAST_TENSE[self]
    except KeyError:
      raise ValueError(f"unsupported job state: {self}")

    md_link = run_md_link(job_key)
    words = [status_emoji, md_link, past_tense]

    if self is JobState.START:
      words.append(f"<t:{START_TS}:R>")
      words.append(f"({RUN_EVENT})")
    else:
      words.append(f"in {format_runtime(START_TS)}")

    if self is JobState.SUCCEEDED and success_commit:
      words.append(
          f"([{success_commit[:7]}](<{REPO_URL}/commit/{success_commit}>))")

    return ' '.join(words)

  def write_env_var(self, job_key: str, success_commit: str | None = None):
    try:
      env_var = JOB_STATE_ENV_VARS[self]
    except KeyError:
      raise ValueError(f"unsupported job state: {self}")

    value = self.title(job_key, success_commit=success_commit)

    if success_commit:
      extra_body = make_success_body(success_commit, len(value))
      value += f"\n{extra_body}"
    elif self is JobState.SUCCEEDED:
      value += " (no changes)"

    with open(GITHUB_ENV_FILE, 'a') as f:
      f.write(f'{env_var}<<EOF\n{value}\nEOF\n\n')


JOB_STATE_ENV_VARS = {
    JobState.START: 'DISCORD_MSG_START',
    JobState.SUCCEEDED: 'DISCORD_MSG_SUCCESS',
    JobState.FAILED: 'DISCORD_MSG_FAIL',
    JobState.CANCELED: 'DISCORD_MSG_CANCEL',
}

JOB_STATE_STATUS_EMOJI = {
    JobState.START: '⚙️',
    JobState.SUCCEEDED: '✅',
    JobState.FAILED: '⚠️',
    JobState.CANCELED: '❌',
}

JOB_STATE_PAST_TENSE = {
    JobState.START: 'started',
    JobState.SUCCEEDED: 'succeeded',
    JobState.FAILED: 'failed',
    JobState.CANCELED: 'canceled',
}


def make_success_body(commit_hash: str, title_len: int) -> str:
  try:
    with open(scrapy_util.DISCORD_STATS_PATH, "r") as f:
      discord_stats = f.read()
  except FileNotFoundError:
    discord_stats = ""

  blocks = []
  if discord_stats:
    blocks.append(discord_stats)

  if commit_hash:
    git_cmd = ['git', 'show', '--stat', '--pretty=oneline', commit_hash]
    diff_stats = subprocess.run(git_cmd, capture_output=True, text=True).stdout
    if diff_stats:
      blocks.append(diff_stats)

  print(f"raw success body:\n{discord_stats}\n{diff_stats}")

  # actual discord cutoff is 2000, but leave some buffer for formatting and
  # title
  msg_cutoff = 1990 - title_len

  block_length = sum(len(b) for b in blocks)
  while block_length > msg_cutoff:
    excess_length = block_length - msg_cutoff
    # trim the start of each block evenly
    trim_per_block = (excess_length // len(blocks)) + 1
    for i in range(len(blocks)):
      # only trim the block if it wouldn't be completely removed by the trim
      # this means we might not actually trim as much as we need and we
      # need to loop a couple times.
      if len(blocks[i]) > trim_per_block:
        blocks[i] = blocks[i][trim_per_block:]

    block_length = sum(len(b) for b in blocks)

  return '\n\n'.join(f"```{b}```" for b in blocks if b)


def run_md_link(job_key: str) -> str:
  job_display = JOB_DISPLAY_NAMES.get(job_key, job_key)
  return f"[{job_display} update #{RUN_NUMBER}](<{RUN_URL}>)"


def format_runtime(start_ts: str | None) -> str | None:
  if not start_ts:
    return None

  try:
    start_epoch = int(start_ts)
  except ValueError:
    return None

  duration = int(time.time()) - start_epoch
  if duration < 0:
    return None

  hours, remainder = divmod(duration, 3600)
  minutes, seconds = divmod(remainder, 60)

  parts = []
  if hours:
    parts.append(f"{hours}h")
  if minutes or hours:
    parts.append(f"{minutes}m")
  parts.append(f"{seconds}s")

  return ' '.join(parts)


if __name__ == '__main__':
  main()
