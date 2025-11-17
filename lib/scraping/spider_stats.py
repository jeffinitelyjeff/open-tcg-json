import enum

from . import scrapy_util


class Notice(enum.Enum):

  @classmethod
  def all_keys(cls):
    return [n.name for n in cls]


class Error(enum.Enum):

  @classmethod
  def all_keys(cls):
    return [e.name for e in cls]


def truthy_print(val):
  if val:
    print(val)


def github_annotation(notice_level: str, spider_name: str, stats: dict,
                      key: str):
  val = stats.get(key, None)
  if val is None:
    return None

  msg = f"{key}: {val:,}"
  return f"::{notice_level} title={spider_name}::{msg}"


# FIXME: move to a spider base class
def print_github_annotations(stats, spider_name):
  for key in Notice.all_keys():
    truthy_print(github_annotation('notice', spider_name, stats, key))

  for key in Error.all_keys():
    truthy_print(github_annotation('error', spider_name, stats, key))


# FIXME: move to a spider base class
def write_discord_lines(stats, spider_name):
  lines = []

  for key in Notice.all_keys() + Error.all_keys():
    if stats.get(key):
      lines.append(f"  {key}: {stats[key]:,}")

  if not lines:
    return

  with open(scrapy_util.DISCORD_STATS_PATH, "a") as f:
    text = f"[{spider_name}]\n" + "\n".join(lines) + "\n"
    f.write(text)


def get_discord_stats():
  try:
    with open(scrapy_util.DISCORD_STATS_PATH, "r") as f:
      return f.read()
  except FileNotFoundError:
    return ""
