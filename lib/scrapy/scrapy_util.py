import asyncio
import collections
import datetime
import functools
import logging
import json
import os
import pathlib
import re
import shutil

RUN_TS = datetime.datetime.now(datetime.timezone.utc)
ROOT_DIR = pathlib.Path(__file__).parent.parent.parent
LOG_DIR = ROOT_DIR / 'logs'
DISCORD_STATS_PATH = LOG_DIR / "discord_stats.txt"


def make_log_dir():
  os.makedirs(LOG_DIR, exist_ok=True)


def response_logger(log_level=logging.DEBUG):

  def decorator(func):

    @functools.wraps(func)
    def wrapper(self, response, *args, **kwargs):
      logging.log(log_level, 'GET %s | %s', response.status, response.url)
      self.crawler.stats.inc_value(f'httpstatus/count/{response.status}')
      try:
        result = func(self, response, *args, **kwargs)
        if hasattr(result, '__iter__') and not isinstance(result, (str, bytes)):
          for item in result:
            yield item
        else:
          return result
      except AssertionError as e:
        raise AssertionError(f"{e} ({response.url})") from e

    return wrapper

  return decorator


log_response_INFO = response_logger(logging.INFO)
log_response_DEBUG = response_logger(logging.DEBUG)


def get_text(element) -> str:
  return ''.join(element.css('::text').getall()).strip()


def get_texts_or_text(element) -> list[str]:
  l = [text.strip() for text in element.css('::text').getall() if text.strip()]
  return l[0] if len(l) == 1 else l


def descendent_text(element) -> str:
  return ''.join(element.css('*::text').getall()).strip()
