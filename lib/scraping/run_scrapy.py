import argparse
import datetime
import json
import logging
from math import log
import os
import shutil
import subprocess

from requests import get
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings, Settings

from .. import util
from .spiders.tcg_plus import TCGPlusCardListSpider

SPIDERS = [
    TCGPlusCardListSpider,
]


def main():
  # args = get_cli_args()

  os.environ.setdefault('SCRAPY_SETTINGS_MODULE', 'lib.scraping.settings')
  scrapy_settings = get_project_settings()
  set_up_logs(scrapy_settings)
  run_spiders(scrapy_settings)
  organize_discord_output()


def get_cli_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser()

  # TODO

  return parser.parse_args()


def set_up_logs(project_settings: Settings):
  util.make_log_dir()
  log_fname = f"run_scrapy.py-{util.RUN_TS:%Y%m%d}.log"
  log_path = util.LOG_DIR / log_fname

  # https://docs.python.org/3/howto/logging-cookbook.html#logging-to-multiple-destinations
  console = logging.StreamHandler()
  console.setLevel(logging.INFO)
  console.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
  logging.getLogger('').addHandler(console)

  project_settings['LOG_FILE'] = log_path


def run_spiders(scrapy_settings: Settings):
  process = CrawlerProcess(scrapy_settings)

  for spider in SPIDERS:
    process.crawl(spider)

  process.start()


def organize_discord_output():
  # FIXME: move to a separate script?
  # -- organize discord message

  discord_stats = stats.get_discord_stats()
  s3_uploads = stats.get_s3_uploads()

  git_cmd1 = ['git', 'diff', '--shortstat']
  diff_summary = subprocess.run(git_cmd1, capture_output=True, text=True).stdout

  git_cmd2 = ['git', 'diff', '--stat']
  diff_stats = subprocess.run(git_cmd2, capture_output=True, text=True).stdout

  run_number = os.environ.get('GITHUB_RUN_NUMBER')
  server_url = os.environ.get('GITHUB_SERVER_URL')
  repo_name = os.environ.get('GITHUB_REPOSITORY')
  run_id = os.environ.get('GITHUB_RUN_ID')

  run_url = f"{server_url}/{repo_name}/actions/runs/{run_id}"
  link = f"[{run_number}]({run_url})"
  msg = f"⚙️  Scraping run #[{run_number}]({run_url}) finished\n"
  msg += "```\n" + discord_stats

  if s3_uploads:
    more_line = f"({len(s3_uploads) - 5} more...)"
    truncated_list = s3_uploads[:5] + [more_line]
    list = truncated_list if len(s3_uploads) > 6 else s3_uploads
    msg += "[S3 Uploads]\n" + '\n'.join('  ' + l for l in list) + '\n'

  if diff_summary:
    parts = diff_summary.split(', ')
    summary_str = '\n'.join('  ' + p.strip() for p in parts)
    msg += "[Diff Summary]\n" + summary_str + "```\n"

  if diff_stats:
    msg += "```\n" + diff_stats

  if len(msg) > 1997:
    msg = msg[:1993] + '...\n'
  msg += "```\n"

  with open('logs/discord_msg.txt', 'w') as f:
    f.write(msg)

  try:
    summary_path = os.environ["GITHUB_STEP_SUMMARY"]
    if s3_uploads:
      with open(summary_path, "r") as f:
        prev_summary = f.read()

      with open(summary_path, 'w') as f:
        uploads_str = '\n'.join('- ' + l for l in s3_uploads)
        f.write("#### S3 Uploads:\n" + uploads_str + "\n\n")
        f.write(prev_summary)

  except KeyError:
    logging.error("no $GITHUB_STEP_SUMMARY env variable")


if __name__ == '__main__':
  main()
