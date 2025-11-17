import enum

from .. import util


class Notice(enum.Enum):

  @classmethod
  def global_keys(cls):
    return []

  @classmethod
  def all_keys(cls):
    return [n.name for n in cls] + cls.global_keys()


class Error(enum.Enum):

  @classmethod
  def global_keys(cls):
    return [
        'log_count/ERROR',
    ]

  @classmethod
  def all_keys(cls):
    return [e.name for e in cls] + cls.global_keys()


DISCORD_PATH = util.LOG_DIR / "discord_stats.txt"


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


def print_github_annotations(stats, spider_name):
  for key in Notice.all_keys():
    truthy_print(github_annotation('notice', spider_name, stats, key))

  for key in Error.all_keys():
    truthy_print(github_annotation('error', spider_name, stats, key))


def write_discord_lines(stats, spider_name):
  lines = []

  for key in Notice.all_keys() + Error.all_keys():
    if stats.get(key):
      lines.append(f"  {key}: {stats[key]:,}")

  if not lines:
    return

  with open(DISCORD_PATH, "a") as f:
    text = f"[{spider_name}]\n" + "\n".join(lines) + "\n"
    f.write(text)


def get_discord_stats():
  try:
    with open(DISCORD_PATH, "r") as f:
      return f.read()
  except FileNotFoundError:
    return ""
