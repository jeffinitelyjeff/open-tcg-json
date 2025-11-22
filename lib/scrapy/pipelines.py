import json
import logging
import os
import shutil

from itemadapter import ItemAdapter

from . import scrapy_util
from .spiders import base_spider


class OTCGJPipeline:

  def open_spider(self, spider):
    logging.info("opening spider %s", spider.name)

    if isinstance(spider, base_spider.BaseSpider):
      spider.maybe_clear_output_dir()

  def close_spider(self, spider):
    logging.info("closing spider %s", spider.name)

    if isinstance(spider, base_spider.BaseSpider):
      spider.append_github_summary()
      spider.write_github_annotations()
      spider.append_discord_stats()
      for path in spider.jsonl_files_written:
        spider.convert_jsonl(path)

  def process_item(self, item, spider):
    logging.debug("processing item for spider %s", spider.name)

    if not item:
      return item

    if not isinstance(item, dict):
      logging.error("%s item is not a dict: %s", spider.name, item)
      return item

    if not isinstance(spider, base_spider.BaseSpider):
      return item

    if spider.write_item_json(item):
      return item

    if spider.write_item_jsonl(item):
      return item

    return item
