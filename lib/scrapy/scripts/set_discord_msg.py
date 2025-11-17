import argparse
import os
import subprocess

from .. import scrapy_util

GITHUB_ENV_FILE = os.getenv('GITHUB_ENV')

RUN_NUMBER = os.getenv('GITHUB_RUN_NUMBER')
SERVER_URL = os.getenv('GITHUB_SERVER_URL')
REPO_NAME = os.getenv('GITHUB_REPOSITORY')
RUN_ID = os.getenv('GITHUB_RUN_ID')

RUN_URL = f"{SERVER_URL}/{REPO_NAME}/actions/runs/{RUN_ID}"
RUN_MD_LINK = f"[Poll run #{RUN_NUMBER}](<{RUN_URL}>)"

START_TS = os.getenv('START_TS')


def main():

  parser = argparse.ArgumentParser()
  group = parser.add_mutually_exclusive_group(required=True)
  group.add_argument('--success', action='store_true')
  group.add_argument('--defaults', action='store_true')
  args = parser.parse_args()

  if args.success:
    msg = make_success_msg()
    with open(GITHUB_ENV_FILE, 'a') as f:
      f.write(f'DISCORD_MSG_SUCCESS<<EOF\n{msg}\nEOF\n')
  else:
    msg_start = f"⚙️  {RUN_MD_LINK} started (<t:{START_TS}:R>)"
    msg_fail = f"⚠️  {RUN_MD_LINK} failed"
    msg_cancel = f"❌  {RUN_MD_LINK} cancelled"
    with open(GITHUB_ENV_FILE, 'a') as f:
      f.write(f'DISCORD_MSG_START={msg_start}\n')
      f.write(f'DISCORD_MSG_FAIL={msg_fail}\n')
      f.write(f'DISCORD_MSG_CANCEL={msg_cancel}\n')


def make_success_msg() -> str:
  try:
    with open(scrapy_util.DISCORD_STATS_PATH, "r") as f:
      discord_stats = f.read()
  except FileNotFoundError:
    discord_stats = ""

  blocks = []
  if discord_stats:
    blocks.append(discord_stats)

  # FIXME
  cwd = os.getcwd()
  print("cwd: ", cwd)
  cwd_otuput = subprocess.run(['pwd'], capture_output=True, text=True).stdout
  print("subprocess cwd: ", cwd_otuput)

  git_cmd = ['git', 'diff', '--stat']
  diff_stats = subprocess.run(git_cmd, capture_output=True, text=True).stdout
  print("git diff --stat output:\n", diff_stats)
  if diff_stats:
    blocks.append(diff_stats)

  title = f"⚙️  {RUN_MD_LINK} finished\n"

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


if __name__ == '__main__':
  main()
