import argparse
import os
import subprocess
import time

from .. import scrapy_util

GITHUB_ENV_FILE = os.getenv('GITHUB_ENV')

RUN_NUMBER = os.getenv('GITHUB_RUN_NUMBER')
SERVER_URL = os.getenv('GITHUB_SERVER_URL')
REPO_NAME = os.getenv('GITHUB_REPOSITORY')
RUN_ID = os.getenv('GITHUB_RUN_ID')

RUN_URL = f"{SERVER_URL}/{REPO_NAME}/actions/runs/{RUN_ID}"
RUN_MD_LINK = f"[Poll run #{RUN_NUMBER}](<{RUN_URL}>)"

START_TS = os.getenv('START_TS')
JOB_DISPLAY_NAMES = {
    'dcg_wiki': 'DCG Wiki scrape',
    'tcg_plus': 'TCG Plus scrape',
}


def main():

  parser = argparse.ArgumentParser()
  parser.add_argument('--job',
                      choices=JOB_DISPLAY_NAMES.keys(),
                      required=True,
                      help='Job identifier for Discord messaging context.')

  group = parser.add_mutually_exclusive_group(required=True)
  group.add_argument('--dcg-wiki-success', action='store_true')
  group.add_argument('--tcg-plus-success', action='store_true')
  group.add_argument('--defaults', action='store_true')
  parser.add_argument('--commit-hash', type=str, nargs='?', default=None)
  args = parser.parse_args()

  validate_job_args(parser, args)

  if args.dcg_wiki_success or args.tcg_plus_success:
    job_key = args.job
    msg = make_success_msg(job_key, args.commit_hash)
    with open(GITHUB_ENV_FILE, 'a') as f:
      f.write(f'DISCORD_MSG_SUCCESS<<EOF\n{msg}\nEOF\n')
  else:
    job_display = job_display_name(args.job)
    msg_start = f"⚙️  {job_display} {RUN_MD_LINK} started (<t:{START_TS}:R>)"
    msg_fail = f"⚠️  {RUN_MD_LINK} failed"
    msg_cancel = f"❌  {RUN_MD_LINK} cancelled"
    with open(GITHUB_ENV_FILE, 'a') as f:
      f.write(f'DISCORD_MSG_START={msg_start}\n')
      f.write(f'DISCORD_MSG_FAIL={msg_fail}\n')
      f.write(f'DISCORD_MSG_CANCEL={msg_cancel}\n')


def make_success_msg(job_key: str, commit_hash: str | None) -> str:
  try:
    with open(scrapy_util.DISCORD_STATS_PATH, "r") as f:
      discord_stats = f.read()
  except FileNotFoundError:
    discord_stats = ""

  blocks = []
  if discord_stats:
    blocks.append(discord_stats)

  print(f"commit_hash: {commit_hash}")  # FIXME

  if commit_hash:
    git_cmd = ['git', 'show', '--stat', '--pretty=oneline', commit_hash]
    diff_stats = subprocess.run(git_cmd, capture_output=True, text=True).stdout
    print(f"diff_stats: {diff_stats}")  # FIXME
    if diff_stats:
      blocks.append(diff_stats)

  job_display = job_display_name(job_key)

  runtime = format_runtime(START_TS)
  runtime_suffix = f" (⏱️ {runtime})" if runtime else ""
  title = f"⚙️  {RUN_MD_LINK} ({job_display}) finished{runtime_suffix}"

  msg = make_msg(title, blocks)

  msg_cutoff = 1997

  if len(msg) > msg_cutoff:
    extra_len = len(msg) - msg_cutoff
    # trim the start of the diff (summary stats are at the end)
    blocks[-1] = blocks[-1][extra_len:]
    msg = make_msg(title, blocks)

  return msg


def make_msg(title, blocks):
  return '\n'.join([title, *[f"```\n{b}\n```" for b in blocks]])


def job_display_name(job_key: str) -> str:
  return JOB_DISPLAY_NAMES.get(job_key, job_key)


def validate_job_args(parser: argparse.ArgumentParser, args):
  flag_job = None
  if args.dcg_wiki_success:
    flag_job = 'dcg_wiki'
  elif args.tcg_plus_success:
    flag_job = 'tcg_plus'
  if flag_job and args.job != flag_job:
    parser.error(f"--job must be '{flag_job}' when using this flag")


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
