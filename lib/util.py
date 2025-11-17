import asyncio
import collections
import datetime
import functools
import json
import os
import pathlib
import re
import shutil

RUN_TS = datetime.datetime.now()
ROOT_DIR = pathlib.Path(__file__).parent.parent
LOG_DIR = ROOT_DIR / 'logs'


def make_log_dir():
  os.makedirs(LOG_DIR, exist_ok=True)
