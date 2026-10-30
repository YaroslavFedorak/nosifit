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
from datetime import date, datetime, time, timezone, tzinfo
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


def local_date(moment: datetime) -> date:
    """The calendar day, in the application's zone, of a naive UTC datetime."""
    return moment.replace(tzinfo=timezone.utc).astimezone(app_timezone()).date()


def to_local_date(moment: datetime) -> date:
    """The calendar day, in the application's zone, of a timezone-aware datetime."""
    return moment.astimezone(app_timezone()).date()


def to_naive_utc(moment: datetime) -> datetime:
    return moment.astimezone(timezone.utc).replace(tzinfo=None)


def day_bounds(day: date) -> tuple[datetime, datetime]:
    """First and last moment of a calendar day in the application's zone."""
    zone = app_timezone()
    return datetime.combine(day, time.min, tzinfo=zone), datetime.combine(day, time.max, tzinfo=zone)


def day_bounds_utc(day: date) -> tuple[datetime, datetime]:
    """:func:`day_bounds` as naive UTC, the way training sessions are stored."""
    start, end = day_bounds(day)
    return to_naive_utc(start), to_naive_utc(end)
