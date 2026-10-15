"""The application's calendar day.

"Today" for nutrition (meals, water, weight, goals) is the day in
``APP_TIMEZONE`` - not whatever the server's local clock says. The zone comes
from, in order: ``APP_TIMEZONE``, ``NOSI_FIT_TIMEZONE`` (the Telegram bot's
setting, so both agree), then ``Europe/Kyiv``. An unknown zone name falls back
to ``Europe/Kyiv`` rather than failing a request.

There is one zone for the whole application (users have no timezone of their
own yet). Tests replace :func:`now` to pin the clock.
"""
from __future__ import annotations

import os
from datetime import date, datetime, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_TIMEZONE = "Europe/Kyiv"


def timezone_name() -> str:
    for key in ("APP_TIMEZONE", "NOSI_FIT_TIMEZONE"):
        value = (os.getenv(key) or "").strip()
        if value:
            return value
    return DEFAULT_TIMEZONE


def app_timezone() -> tzinfo:
    try:
        return ZoneInfo(timezone_name())
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo(DEFAULT_TIMEZONE)


def now() -> datetime:
    """The current moment, timezone-aware, in the application's zone."""
    return datetime.now(app_timezone())


def today() -> date:
    return now().date()
