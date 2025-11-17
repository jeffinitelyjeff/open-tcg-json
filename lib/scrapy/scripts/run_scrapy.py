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

from .. import scrapy_util
from ..spiders import tcg_plus

SPIDERS = [
    tcg_plus.TCGPlusSpider,
]


def main():
  # args = get_cli_args()

  os.environ.setdefault('SCRAPY_SETTINGS_MODULE', 'lib.scrapy.settings')
  scrapy_settings = get_project_settings()
  set_up_logs(scrapy_settings)
  run_spiders(scrapy_settings)


def get_cli_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser()

  # TODO

  return parser.parse_args()


def set_up_logs(project_settings: Settings):
  scrapy_util.make_log_dir()
  log_fname = f"run_scrapy.py-{scrapy_util.RUN_TS:%Y%m%d}.log"
  log_path = scrapy_util.LOG_DIR / log_fname

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


if __name__ == '__main__':
  main()
