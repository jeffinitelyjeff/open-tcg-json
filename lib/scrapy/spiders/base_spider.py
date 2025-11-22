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
