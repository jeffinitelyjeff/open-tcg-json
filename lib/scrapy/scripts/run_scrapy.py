import argparse
import logging
import os
import sys

from scrapy.crawler import CrawlerProcess
from scrapy.utils import project

from .. import scrapy_util
from ..spiders import tcg_plus
from ..spiders import dcg_wiki

SPIDERS = {
    "dcg_wiki": dcg_wiki.DCGWikiSpider,
    "tcg_plus": tcg_plus.TCGPlusSpider,
}


def main():
  args = get_cli_args()

  os.environ.setdefault('SCRAPY_SETTINGS_MODULE', 'lib.scrapy.settings')
  scrapy_settings = project.get_project_settings()
  set_up_logs(scrapy_settings)

  logging.info("CLI args: %s", args)

  run_spiders(scrapy_settings, args)


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
  selected_spiders = []
  for spider_name, spider in SPIDERS.items():
    if args.all or getattr(args, spider_name):
      selected_spiders.append((spider_name, spider))
    else:
      logging.info("Spider %s ==> ❌ skipped", spider_name)

  if not selected_spiders:
    logging.info("No spiders selected; exiting.")
    return

  run_spiders_parallel(scrapy_settings, selected_spiders)


def run_spiders_parallel(scrapy_settings: project.Settings, selected_spiders):
  process = CrawlerProcess(scrapy_settings)

  crawlers = []

  for spider_name, spider in selected_spiders:
    logging.info("Spider %s ==> start (parallel)", spider_name)
    crawler = process.create_crawler(spider)
    crawlers.append((crawler, spider_name))
    process.crawl(crawler)

  process.start()

  for crawler, spider_name in crawlers:
    spider_label = crawler.spider.name if crawler.spider else spider_name
    finish_reason = crawler.stats.get_value('finish_reason')
    if finish_reason and finish_reason != 'finished':
      raise RuntimeError(
          f"Spider [{spider_label}] stopped early ({finish_reason})")

    error_count = crawler.stats.get_value('log_count/ERROR', 0)
    if error_count > 0:
      msg = f"Spider [{spider_label}] encountered {error_count} errors"
      raise RuntimeError(msg)


if __name__ == '__main__':
  main()
