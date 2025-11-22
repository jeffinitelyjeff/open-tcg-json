import json
import logging
import os
import pathlib
import shutil
from typing import Text

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
        JSONLItem.convert_to_json(path)

  def process_item(self, item, spider):
    logging.debug("processing item for spider %s", spider.name)

    if not item:
      return item

    if not isinstance(spider, base_spider.BaseSpider):
      return item

    supportedItems = [JSONItem, JSONLItem, TextItem]
    for cls in supportedItems:
      if isinstance(item, cls):
        item.write(spider)
        return item

    return item


class BaseItem:
  required_extension = None

  def __init__(self,
               path: pathlib.Path | None = None,
               subpath: list[str] | None = None):
    assert path or subpath, "either path or subpath must be provided"
    self.path = path
    self.subpath = subpath

    if self.required_extension:
      last_item = self.path or self.subpath[-1]
      msg = f"path must end in {self.required_extension}: {last_item}"
      assert last_item.endswith(self.required_extension), msg

  def full_path(self, spider: base_spider.BaseSpider) -> pathlib.Path:
    p = spider.full_path(self.path, self.subpath)
    if self.required_extension:
      assert p.suffix == self.required_extension, \
        f"path must end in {self.required_extension}: {p}"
    return p


class JSONItem(BaseItem):

  required_extension = '.json'

  def __init__(self, data: any, **kwargs):
    super().__init__(**kwargs)
    self.data = data

  def write(self, spider: base_spider.BaseSpider):
    full_path = self.full_path(spider)

    os.makedirs(full_path.parent, exist_ok=True)
    with open(full_path, 'w', encoding='utf-8') as f:
      json.dump(self.data, f, ensure_ascii=False, indent=2, sort_keys=True)


class JSONLItem(BaseItem):

  required_extension = '.jsonl'

  def __init__(self, data: any, sort: any, **kwargs):
    super().__init__(**kwargs)
    self.data = data
    self.sort = sort

  def write(self, spider: base_spider.BaseSpider):
    full_path = self.full_path(spider)

    os.makedirs(full_path.parent, exist_ok=True)
    with open(full_path, 'a', encoding='utf-8') as f:
      jsonl_data = {'sort': self.sort, 'data': self.data}
      f.write(json.dumps(jsonl_data, ensure_ascii=False) + '\n')

    if not spider.jsonl_files_written:
      spider.jsonl_files_written = set()

    spider.jsonl_files_written.add(full_path)

  @staticmethod
  def convert_to_json(path: pathlib.Path):
    assert path.suffix == '.jsonl', "path must end in .jsonl"
    json_path = path.with_suffix('.json')

    data_list = []
    sort_list = []
    with open(path, 'r', encoding='utf-8') as f:
      for line in f:
        json_data = json.loads(line)
        sort_list.append(json_data['sort'])
        data_list.append(json_data['data'])

    sorted_data = [item for _, item in sorted(zip(sort_list, data_list))]

    with open(json_path, 'w', encoding='utf-8') as f:
      json.dump(sorted_data, f, ensure_ascii=False, indent=2, sort_keys=True)

    logging.info("converted: %s -> .json", path)
    os.remove(path)


class TextItem(BaseItem):
  required_extension = None

  def __init__(self, data: str, **kwargs):
    super().__init__(**kwargs)
    self.data = data

  def write(self, spider: base_spider.BaseSpider):
    full_path = self.full_path(spider)

    os.makedirs(full_path.parent, exist_ok=True)
    with open(full_path, 'w', encoding='utf-8') as f:
      f.write(self.data)
