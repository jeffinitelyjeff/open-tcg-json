import enum
import json
import logging
import os
import pathlib
import pprint

import scrapy

from .. import scrapy_util
from ... import util


class Notice(enum.Enum):

  @classmethod
  def all_keys(cls):
    return [n.name for n in cls]


class Error(enum.Enum):

  @classmethod
  def all_keys(cls):
    return [e.name for e in cls]

  def log(self, message: str):
    logging.error(f"{self.name}: {message}")


class BaseSpider(scrapy.Spider):
  # scrapy properties
  name = "OTCGJson Base Spider [this should be overriden!]"

  # custom properties
  output_dir: scrapy_util.Path | None = None
  clear_output_dir = False
  notice_keys: list[str] = []
  error_keys: list[str] = []

  def maybe_clear_output_dir(self):
    if self.clear_output_dir and self.output_dir and self.output_dir.exists():
      scrapy_util.rmtree(self.output_dir)

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
    return f"::{notice_level} title={self.name}::{msg}"

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

  def full_path(self, subpath: list[str]) -> pathlib.Path:
    assert self.output_dir is not None, "spider.output_dir must be set"
    return self.output_dir.joinpath(*subpath)

  def write(self,
            data: dict,
            subpath: list[str] | None = None,
            path: pathlib.Path | None = None):
    if path:
      full_path = path
    else:
      assert self.output_dir is not None, "spider.output_dir must be set"
      assert subpath is not None, "either subpath or path must be set"
      full_path = self.output_dir.joinpath(*subpath)

    os.makedirs(full_path.parent, exist_ok=True)
    with open(full_path, 'w', encoding='utf-8') as f:
      json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
