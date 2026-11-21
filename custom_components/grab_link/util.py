"""Helpers for the Grab Link Tracking integration."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.util import dt as dt_util


def parse_timestamp_value(value: Any) -> datetime | None:
    """Parse a unix timestamp or an ISO datetime string into a datetime.

    Returns None when the value is missing or cannot be parsed.
    """
    if value is None or value == "":
        return None

    if isinstance(value, (int, float)):
        return _from_unix(value)

    parsed = dt_util.parse_datetime(str(value))
    if parsed is not None:
        return parsed

    try:
        return _from_unix(float(value))
    except (TypeError, ValueError):
        return None


def _from_unix(timestamp: float) -> datetime | None:
    """Convert a unix timestamp into a UTC datetime."""
    try:
        return datetime.fromtimestamp(timestamp, tz=dt_util.UTC)
    except (OverflowError, OSError, ValueError):
        return None
