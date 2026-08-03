"""Shared helpers for filtering global-source jobs by post date.

Each source's API represents "posted" differently (Unix epoch, ISO8601
string, feedparser's UTC struct_time) so parsing is centralized here rather
than duplicated per source.
"""

from __future__ import annotations

import calendar
import time
from datetime import datetime, timezone


def parse_posted_at(value: int | float | str | time.struct_time | None) -> datetime | None:
    """Best-effort parse of a source's raw posted-date value to a tz-aware
    UTC datetime. Returns None if missing or unparseable."""
    if value is None:
        return None

    if isinstance(value, time.struct_time):
        # feedparser normalizes *_parsed fields to UTC already, so treat the
        # struct_time as UTC (calendar.timegm) rather than local time
        # (time.mktime, which would apply the wrong offset).
        return datetime.fromtimestamp(calendar.timegm(value), tz=timezone.utc)

    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc)
        except (ValueError, OSError, OverflowError):
            return None

    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    return None


def is_within_window(raw_posted: int | float | str | time.struct_time | None, since: datetime | None) -> bool:
    """Keep the job if no cutoff is set, or its posted date can't be
    determined (never drop a listing just because parsing failed), or it
    was posted on/after `since`."""
    if since is None:
        return True
    posted_at = parse_posted_at(raw_posted)
    if posted_at is None:
        return True
    return posted_at >= since
