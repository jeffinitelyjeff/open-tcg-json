import enum
import inspect
import json
import logging
import os
import pathlib
import pprint
import shutil

import scrapy

from .. import scrapy_util
from ... import util


def github_annotation(notice_level: str, fields: dict[str, str],
                      message: str) -> str:
  fields_str = ','.join(f"{k}={v}" for k, v in fields.items())
  return f"::{notice_level} {fields_str}::{message}"


class Error(enum.Enum):
  """
  Each error is printed out as a Github Actions annotation, tied to the file
  and line where it occurred.
  """

  @classmethod
  def all_keys(cls):
    return [e.name for e in cls]


class Notice(enum.Enum):
  """
  Notices aren't reported as individual Github Actions annotations, but are
  aggregated via spider stats and reported as a total count.
  """

  @classmethod
  def all_keys(cls):
    return [n.name for n in cls]


class BaseSpider(scrapy.Spider):
  # scrapy properties
  name = "OTCGJson Base Spider [this should be overriden!]"

  # custom properties
  output_dir: pathlib.Path | None = None
  clear_output_dir = False
  notice_keys: list[str] = []
  error_keys: list[str] = []

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.jsonl_files_written: set[pathlib.Path] = set()

  def log_error(self, error: Error, message: str):
    caller = inspect.getframeinfo(inspect.stack()[1][0])
    logging.error(f"{error.name}: {message}")
    fields = {
        'title': error.name,
        'file': caller.filename,
        'line': caller.lineno,
    }
    print(github_annotation('error', fields, message))
    self.crawler.stats.inc_value(error.name)

  def log_notice(self, notice: Notice, message: str):
    logging.info(f"{notice.name}: {message}")
    self.crawler.stats.inc_value(notice.name)

  def maybe_clear_output_dir(self):
    if self.clear_output_dir and self.output_dir and self.output_dir.exists():
      shutil.rmtree(self.output_dir)

  def append_github_summary(self):
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    stats = self.crawler.stats.get_stats()
    if summary_path:
      lines = [
          "<details>",
          f"<summary>{self.name} Stats</summary>",
          "",
          "```",
          pprint.pformat(stats),
          "```",
          "",
          "</details>",
      ]
      with open(summary_path, "a") as f:
        f.write("\n".join(lines))

  def github_annotation(self, notice_level: str, key: str) -> str | None:
    val = self.crawler.stats.get(key, None)
    if val is None:
      return None

    msg = f"{key}: {val:,}"
    return github_annotation(notice_level, {'title': self.name}, msg)

  def write_github_annotations(self):
    # FIXME: emit these annotations when the error/notice actually occurs,
    # instead of the aggregated stat at the end. keep the aggregated stat for
    # discord.

    # github actions annotations are written to stdout
    # https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#setting-a-warning-message

    for key in self.notice_keys:
      util.truthy_print(self.github_annotation('notice', key))

    for key in self.error_keys:
      util.truthy_print(self.github_annotation('error', key))

  def append_discord_stats(self):
    lines = []

    for key in self.notice_keys:
      if self.crawler.stats.get(key):
        lines.append(f"  {key}: {self.crawler.stats[key]:,}")

    for key in self.error_keys:
      if self.crawler.stats.get(key):
        lines.append(f"  ⚠️ {key}: {self.crawler.stats[key]:,}")

    if not lines:
      return

    with open(scrapy_util.DISCORD_STATS_PATH, "a") as f:
      text = f"[{self.name}]\n" + "\n".join(lines) + "\n"
      f.write(text)

  def full_path(
      self,
      path: pathlib.Path | None = None,
      subpath: list[str] | None = None,
  ) -> pathlib.Path:
    if path:
      return path

    assert subpath, "either path or subpath must be provided"
    assert self.output_dir, "output_dir must be set to use subpath"
    return self.output_dir.joinpath(*subpath)

  def write_item_json(self, item: dict) -> bool:
    path = item.pop('json_path', None)
    subpath = item.pop('json_subpath', None)
    if not path and not subpath:
      return False

    full_path = self.full_path(path, subpath)
    assert full_path.suffix == '.json', "json path must end in .json"

    os.makedirs(full_path.parent, exist_ok=True)
    with open(full_path, 'w', encoding='utf-8') as f:
      json.dump(item, f, ensure_ascii=False, indent=2, sort_keys=True)

    return True

  def write_item_jsonl(self, item: dict) -> bool:
    path = item.pop('jsonl_path', None)
    subpath = item.pop('jsonl_subpath', None)
    if not path and not subpath:
      return False

    full_path = self.full_path(path, subpath)
    assert full_path.suffix == '.jsonl', f"{full_path} must end in .jsonl"

    data = item.pop('jsonl_data', None)
    assert data is not None, "jsonl requires jsonl_data field"

    sort = item.pop('jsonl_sort', None)
    assert sort is not None, "jsonl requires jsonl_sort field"

    self.jsonl_files_written.add(full_path)
    os.makedirs(full_path.parent, exist_ok=True)
    with open(full_path, 'a', encoding='utf-8') as f:
      jsonl_data = {'sort': sort, 'data': data}
      f.write(json.dumps(jsonl_data, ensure_ascii=False) + '\n')

  def convert_jsonl(self, path: pathlib.Path):
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

    logging.info("converted: %s -> %s", path, json_path)
    os.remove(path)
