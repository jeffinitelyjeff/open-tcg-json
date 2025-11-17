import json
import logging
import os
import shutil

from itemadapter import ItemAdapter


class OTCGJPipeline:

  def open_spider(self, spider):
    logging.info("opening spider %s", spider.name)

    if getattr(spider, 'clear_output_dir', False):
      if spider.output_dir.exists():
        logging.info("Clearing output directory %s", spider.output_dir)
        shutil.rmtree(spider.output_dir)

  def close_spider(self, spider):
    logging.info("closing spider %s", spider.name)

  def process_item(self, item, spider):
    logging.debug("processing item for spider %s", spider.name)

    if not item:
      return item

    if not isinstance(item, dict):
      logging.error("%s item is not a dict: %s", spider.name, item)
      return item

    write_path = item.pop('write_path', None)
    logging.debug("processing item for %s: %s", spider.name, write_path)
    if write_path:
      self.handle_write_path(spider, write_path, item)

    return item

  def handle_write_path(self, spider, write_path: list[str], data: dict):
    spider_output_path = spider.output_dir
    assert spider_output_path is not None, "spider.output_dir must be set"

    full_path = spider_output_path.joinpath(*write_path)
    logging.debug("writing data to %s", full_path)

    os.makedirs(full_path.parent, exist_ok=True)
    with open(full_path, 'w', encoding='utf-8') as f:
      json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
