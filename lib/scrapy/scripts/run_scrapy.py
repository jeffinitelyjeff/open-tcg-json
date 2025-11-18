import argparse
import logging
import os
import sys

from scrapy import crawler
from scrapy.utils import project

from .. import scrapy_util
from ..spiders import tcg_plus

SPIDERS = [
    tcg_plus.TCGPlusSpider,
]

HIT_ERROR = False


def main():
  # args = get_cli_args()

  os.environ.setdefault('SCRAPY_SETTINGS_MODULE', 'lib.scrapy.settings')
  scrapy_settings = project.get_project_settings()
  set_up_logs(scrapy_settings)
  run_spiders(scrapy_settings)

  if HIT_ERROR:
    sys.exit(1)


def get_cli_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser()

  # TODO

  return parser.parse_args()


def set_up_logs(project_settings: project.Settings):
  scrapy_util.make_log_dir()
  log_fname = f"run_scrapy.py-{scrapy_util.RUN_TS:%Y%m%d}.log"
  log_path = scrapy_util.LOG_DIR / log_fname

  # https://docs.python.org/3/howto/logging-cookbook.html#logging-to-multiple-destinations
  console = logging.StreamHandler()
  console.setLevel(logging.INFO)
  console.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
  logging.getLogger('').addHandler(console)

  project_settings['LOG_FILE'] = log_path


def run_spiders(scrapy_settings: project.Settings):
  process = crawler.CrawlerProcess(scrapy_settings)

  for spider in SPIDERS:
    process.crawl(spider)

  process.start()


if __name__ == '__main__':
  main()
