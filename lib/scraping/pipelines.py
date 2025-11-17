import json
import logging
import os
import shutil

from itemadapter import ItemAdapter

from . import scrapy_util


class OTCGJPipeline:

  # FIXME: move this stuff to spider subclass methods?

  def open_spider(self, spider):
    logging.info("opening spider %s", spider.name)

    if getattr(spider, 'clear_output_dir', False):
      if spider.output_dir.exists():
        logging.info("Clearing output directory %s", spider.output_dir)
        shutil.rmtree(spider.output_dir)

  def close_spider(self, spider):
    logging.info("closing spider %s", spider.name)

  # def close_spider(self, spider):
  #   for f in self.files.values():
  #     f.close()

  #   try:
  #     summary_path = os.environ["GITHUB_STEP_SUMMARY"]
  #   except KeyError:
  #     logging.warning("no $GITHUB_STEP_SUMMARY env variable")
  #     summary_path = None

  #   spider_stats = spider.crawler.stats.get_stats()

  #   if summary_path:
  #     header = f"#### {spider.name} stats:\n\n```\n"
  #     with open(summary_path, "a") as f:
  #       f.write(header + pprint.pformat(spider_stats) + "\n```\n\n")

  #   stats.print_github_annotations(spider_stats, spider.name)
  #   stats.write_discord_lines(spider_stats, spider.name)

  def process_item(self, item, spider):
    logging.debug("processing item for spider %s", spider.name)

    if not item:
      return item

    if not isinstance(item, dict):
      logging.error("%s item is not a dict: %s", spider.name, item)
      return item

    write_path = item.pop('write_path', None)
    write_subpath = item.pop('write_subpath', None)

    if write_path or write_subpath:
      self.handle_write_subpath(spider, write_subpath, write_path, item)
    return item

  def handle_write_subpath(self, spider, write_subpath: list[str] | None,
                           write_path: str | None, data: dict):
    if write_path:
      full_path = write_path
    else:
      spider_output_path = spider.output_dir
      assert spider_output_path is not None, "spider.output_dir must be set"
      full_path = spider_output_path.joinpath(*write_subpath)

    logging.debug("writing data to %s", full_path)

    os.makedirs(full_path.parent, exist_ok=True)
    with open(full_path, 'w', encoding='utf-8') as f:
      json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
