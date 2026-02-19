from __future__ import annotations

import argparse
import datetime
import json
import os
import sys

# Point Pywikibot at the directory that contains the local config files.
os.environ['PYWIKIBOT_DIR'] = os.path.dirname(os.path.abspath(__file__))

import pywikibot


def _parse_since(value: str) -> datetime.datetime:
  """Validate --since input and return a UTC datetime."""
  sanitized = value.strip()
  if sanitized.upper().endswith('Z'):
    sanitized = sanitized[:-1] + '+00:00'
  try:
    parsed = datetime.datetime.fromisoformat(sanitized)
  except ValueError:
    raise argparse.ArgumentTypeError(
        '--since must be ISO 8601 (YYYY-MM-DD or YYYY-MM-DDTHH:MM[:SS][±HH:MM])'
    ) from None

  if parsed.tzinfo is None:
    parsed = parsed.replace(tzinfo=datetime.timezone.utc)
  else:
    parsed = parsed.astimezone(datetime.timezone.utc)

  return parsed


def _to_pywikibot_timestamp(value: datetime.datetime) -> pywikibot.Timestamp:
  utc_value = value.astimezone(datetime.timezone.utc)
  return pywikibot.Timestamp(
      utc_value.year,
      utc_value.month,
      utc_value.day,
      utc_value.hour,
      utc_value.minute,
      utc_value.second,
  )


def _build_arg_parser() -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(
      description='List Digimon Card Game wiki recent changes since a timestamp.'
  )
  parser.add_argument(
      '--since',
      required=True,
      type=_parse_since,
      help=(
          'ISO 8601 timestamp (date or datetime). Timezone offsets are allowed, '
          'otherwise UTC is assumed.'),
  )
  parser.add_argument(
      '--limit',
      type=int,
      default=100,
      help='Maximum number of changes to fetch (default: 100).',
  )
  parser.add_argument(
      '--json',
      action='store_true',
      help='Emit machine-readable JSON instead of plain text.',
  )
  return parser


def _normalize_change(change: dict) -> dict:
  timestamp = change.get('timestamp')
  if isinstance(timestamp, (pywikibot.Timestamp, datetime.datetime)):
    ts_iso = timestamp.isoformat()
  else:
    ts_iso = str(timestamp)
  return {
      'timestamp': ts_iso,
      'title': change.get('title', ''),
      'user': change.get('user', ''),
      'comment': change.get('comment', ''),
      'type': change.get('type', ''),
      'old_revid': change.get('old_revid'),
      'revid': change.get('revid'),
  }


def _print_text(records: list[dict]) -> None:
  if not records:
    print('No recent changes found for the provided window.', file=sys.stderr)
    return
  for record in records:
    comment = record['comment'] or ''
    title = record['title'] or ''
    print(
        f"{record['timestamp']} | {record['user']} | {title} | {record['type']} | {comment}"
    )


def main() -> None:
  parser = _build_arg_parser()
  args = parser.parse_args()

  if args.limit <= 0:
    parser.error('--limit must be a positive integer')

  since_ts = _to_pywikibot_timestamp(args.since)

  site = pywikibot.Site('en', 'dcg')
  site.login()

  changes = site.recentchanges(start=since_ts, reverse=True, total=args.limit)
  records = [_normalize_change(change) for change in changes]

  if args.json:
    json.dump(records, sys.stdout, indent=2)
    sys.stdout.write('\n')
  else:
    _print_text(records)


if __name__ == '__main__':
  main()
