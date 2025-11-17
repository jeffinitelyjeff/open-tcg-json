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
RUN_MD_LINK = f"[{RUN_NUMBER}]({RUN_URL})"

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
    msg_start = f"⚙️  Poll run #{RUN_MD_LINK} started (<t:{START_TS}:R>)"
    msg_fail = f"⚠️  Poll run #{RUN_MD_LINK} failed"
    msg_cancel = f"❌  Poll run #{RUN_MD_LINK} cancelled"
    with open(GITHUB_ENV_FILE, 'a') as f:
      f.write(f'DISCORD_MSG_START={msg_start}\n')
      f.write(f'DISCORD_MSG_FAIL={msg_fail}\n')
      f.write(f'DISCORD_MSG_CANCEL={msg_cancel}\n')


def make_success_msg() -> str:
  try:
    with open(scrapy_util.DISCORD_STATS_PATH, "r") as f:
      discord_stats = f.read()
  except FileNotFoundError:
    discord_stats = "No stats found."

  git_cmd1 = ['git', 'diff', '--shortstat']
  diff_summary = subprocess.run(git_cmd1, capture_output=True, text=True).stdout

  git_cmd2 = ['git', 'diff', '--stat']
  diff_stats = subprocess.run(git_cmd2, capture_output=True, text=True).stdout

  msg = f"⚙️  Poll run #{RUN_MD_LINK} finished\n"
  msg += "```\n" + discord_stats

  if diff_summary:
    parts = diff_summary.split(', ')
    summary_str = '\n'.join('  ' + p.strip() for p in parts)
    msg += "[Diff Summary]\n" + summary_str + "```\n"

  if diff_stats:
    msg += "```\n" + diff_stats

  if len(msg) > 1997:
    msg = msg[:1993] + '...\n'
  msg += "```\n"

  return msg


if __name__ == '__main__':
  main()
