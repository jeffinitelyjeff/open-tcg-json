import os
import subprocess

from .. import scrapy_util


def main():
  try:
    with open(scrapy_util.DISCORD_STATS_PATH, "r") as f:
      discord_stats = f.read()
  except FileNotFoundError:
    discord_stats = "No stats found."

  git_cmd1 = ['git', 'diff', '--shortstat']
  diff_summary = subprocess.run(git_cmd1, capture_output=True, text=True).stdout

  git_cmd2 = ['git', 'diff', '--stat']
  diff_stats = subprocess.run(git_cmd2, capture_output=True, text=True).stdout

  run_number = os.getenv('GITHUB_RUN_NUMBER')
  server_url = os.getenv('GITHUB_SERVER_URL')
  repo_name = os.getenv('GITHUB_REPOSITORY')
  run_id = os.getenv('GITHUB_RUN_ID')

  run_url = f"{server_url}/{repo_name}/actions/runs/{run_id}"
  link = f"[{run_number}]({run_url})"
  msg = f"⚙️  Poll run #{link} finished\n"
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

  github_env_file = os.getenv('GITHUB_ENV')
  with open(github_env_file, 'a') as f:
    f.write(f'DISCORD_MSG<<EOF\n{msg}\nEOF\n')


if __name__ == '__main__':
  main()
