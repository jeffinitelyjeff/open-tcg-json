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
