"""
Parses every timestamp format found in transactions_DA.json.

Verified against the actual 10,000-row dataset (not just the brief):
  1. ISO 8601 with Z:       "2025-10-03T21:03:27Z"        (5,476 records)
  2. Unix milliseconds:      1768265109000 (int/float)      (1,007 records)
  3. Date only:               "2025-07-03"                   (715 records)
  4. DD/MM/YYYY HH:MM:SS:     "12/10/2025 16:24:49"          (841 records)
  5. ISO 8601 with +05:30:    "2026-01-28T13:41:04+05:30"    (1,961 records)

Note: an earlier draft of the spec described format 5 as "ISO, no timezone" —
that's incorrect. The actual records carry an explicit +05:30 (IST) offset.
dateutil handles this correctly either way, so no special-case was needed,
but the docstring is corrected here for anyone reading this later.
"""

import re
from datetime import datetime, timezone

from dateutil import parser as dateutil_parser

# Matches DD/MM/YYYY or DD/MM/YYYY HH:MM:SS — must be checked before the
# generic dateutil parse, since dateutil defaults to MM/DD/YYYY (US-style)
# and would silently misparse e.g. "12/10/2025" as Dec 10 instead of 10 Dec.
_SLASH_DATE_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})(.*)$")


def parse_timestamp(raw: str | int | float) -> datetime:
    """
    Parse any of the 5 known timestamp formats into a timezone-aware UTC datetime.
    Raises ValueError if the value cannot be parsed at all (caller should catch
    and skip/flag the row rather than crash the whole seed run).
    """
    if isinstance(raw, (int, float)):
        # Unix milliseconds -> seconds. (10,000-row dataset never uses unix
        # seconds, only ms — values are consistently 13 digits.)
        return datetime.fromtimestamp(raw / 1000, tz=timezone.utc)

    raw = str(raw).strip()
    if not raw:
        raise ValueError("empty timestamp")

    slash_match = _SLASH_DATE_RE.match(raw)
    if slash_match:
        day, month, year, rest = slash_match.groups()
        rebuilt = f"{year}-{int(month):02d}-{int(day):02d}{rest}"
        dt = dateutil_parser.parse(rebuilt)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    # ISO 8601 with Z, ISO 8601 with +HH:MM offset, and date-only strings are
    # all handled natively and correctly by dateutil.
    dt = dateutil_parser.parse(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
