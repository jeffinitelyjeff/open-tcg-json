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
ROOT_DIR = pathlib.Path(__file__).parent.parent
LOG_DIR = ROOT_DIR / 'logs'
POLL_PATH = ROOT_DIR / 'latest_polls.json'


def make_log_dir():
  os.makedirs(LOG_DIR, exist_ok=True)


# FIXME: move these into a scrapy_util.py file?
def check_poll_threshold(poll_id: str, threshold_seconds: int) -> bool:
  """Check if the poll threshold has been exceeded for the given poll ID.

  Args:
    poll_id: The unique identifier for the poll.
    threshold_seconds: The threshold in seconds.

  Returns:
    True if the threshold has been exceeded, False otherwise.
  """

  if not POLL_PATH.exists():
    logging.info("poll path %s does not exist, proceeding with poll", POLL_PATH)
    return True

  with open(POLL_PATH, 'r', encoding='utf-8') as f:
    last_polls = json.load(f)

  last_poll_ts = last_polls.get(poll_id)
  if not last_poll_ts:
    logging.info("no last poll timestamp found for %s, proceeding with poll",
                 poll_id)
    return True

  last_poll_dt = datetime.datetime.fromisoformat(last_poll_ts)
  if last_poll_dt.tzinfo is None:
    last_poll_dt = last_poll_dt.replace(tzinfo=datetime.timezone.utc)
  elapsed = (RUN_TS - last_poll_dt).total_seconds()
  if elapsed >= threshold_seconds:
    logging.debug(
        "poll threshold exceeded for %s: (%s >= %s), proceeding with poll",
        poll_id, elapsed, threshold_seconds)
    return True
  else:
    logging.info("poll threshold not exceeded for %s: (%s < %s), skipping poll",
                 poll_id, elapsed, threshold_seconds)
    return False


def update_poll_timestamp(poll_id: str):
  """Update the poll timestamp for the given poll ID to the current time.

  Args:
    poll_id: The unique identifier for the poll.
  """

  last_polls = {}
  if POLL_PATH.exists():
    with open(POLL_PATH, 'r', encoding='utf-8') as f:
      last_polls = json.load(f)

  last_polls[poll_id] = RUN_TS.astimezone(datetime.timezone.utc).isoformat()

  with open(POLL_PATH, 'w', encoding='utf-8') as f:
    json.dump(last_polls, f, ensure_ascii=False, indent=2, sort_keys=True)
