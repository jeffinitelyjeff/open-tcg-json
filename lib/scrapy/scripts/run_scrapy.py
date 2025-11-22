import argparse
import logging
import os
import sys

from scrapy import crawler
from scrapy.utils import project

from .. import scrapy_util
from ..spiders import tcg_plus
from ..spiders import dcg_wiki

SPIDERS = {
    "tcg_plus": tcg_plus.TCGPlusSpider,
    "dcg_wiki": dcg_wiki.DCGWikiSpider,
}

HIT_ERROR = False


def main():
  args = get_cli_args()

  os.environ.setdefault('SCRAPY_SETTINGS_MODULE', 'lib.scrapy.settings')
  scrapy_settings = project.get_project_settings()
  set_up_logs(scrapy_settings)

  logging.info("CLI args: %s", args)

  run_spiders(scrapy_settings, args)

  if HIT_ERROR:
    sys.exit(1)


def get_cli_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser()
  spider_group = parser.add_mutually_exclusive_group()
  spider_group.add_argument('--all',
                            action='store_true',
                            help='Run all spiders.')
  for spider_name in SPIDERS:
    spider_group.add_argument(f'--{spider_name}',
                              action='store_true',
                              help=f'Run the {spider_name} spider.')

  args = parser.parse_args()
  return args


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


def run_spiders(scrapy_settings: project.Settings, args: argparse.Namespace):
  process = crawler.CrawlerProcess(scrapy_settings)

  for spider_name, spider in SPIDERS.items():
    if args.all or getattr(args, spider_name):
      logging.info("Spider %s ==> start", spider_name)
      process.crawl(spider)
    else:
      logging.info("Spider %s ==> ❌ skipped", spider_name)

  process.start()


if __name__ == '__main__':
  main()
