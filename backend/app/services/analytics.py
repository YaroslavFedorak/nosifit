"""Aggregate product analytics for the admin dashboard.

Everything is a PostgreSQL aggregate over a bounded date range: nothing is
loaded row by row and nothing user-level leaves this module (only counts).
All days are UTC.

Two kinds of numbers, kept apart in the result:

* ``history``: derived from records users already created (registrations,
  meals, workouts ...). Available for the whole history of the app.
* ``tracked``: derived from ``activity_events``, written since tracking was
  deployed. Active users (DAU/WAU/MAU) and retention exist only from then.

An *active user* on a day is a user with at least one activity event that
day: a successful meal/water/weight/workout/sleep/habit action. Page views
and background requests never count.
"""

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import text

from backend.app.extensions import db

RANGES = {"7": 7, "30": 30, "90": 90, "all": None}
MAX_ALL_DAYS = 3660
# Feature "growing / declining" needs at least this many records before.
MIN_PREVIOUS_RECORDS = 5
TREND_THRESHOLD = 0.2

# key -> (label, from/where clause with {d} for the date expression, user column,
# date expression, extra where). Fixed strings: no user input reaches the SQL.
FEATURES = {
    "food": ("Харчування (прийоми їжі)", "meals", "user_id", "date", "TRUE"),
    "water": ("Вода", "user_water", "user_id", "date", "TRUE"),
    "weight": ("Вага тіла", "user_weight_history", "user_id", "date", "TRUE"),
    "training": (
        "Тренування (сесії)",
        "training_sessions",
        "user_id",
        "CAST(started_at AS date)",
        "TRUE",
    ),
    "sleep": (
        "Сон",
        "recovery_sleep_entries",
        "user_id",
        # timestamptz: a plain cast would use the session TimeZone.
        "CAST((created_at AT TIME ZONE 'UTC') AS date)",
        "TRUE",
    ),
    "habits": (
        "Звички (виконано)",
        "recovery_habit_logs",
        "user_id",
        "CAST((completed_at AT TIME ZONE 'UTC') AS date)",
        "completed IS TRUE AND completed_at IS NOT NULL",
    ),
}


def today_utc() -> date:
    return datetime.now(timezone.utc).date()


def _start_of(day: date) -> datetime:
    return datetime.combine(day, time.min)


def resolve_range(range_key: str, end: date | None = None):
    """(start, end) inclusive, or ValueError for an unknown range."""
    if range_key not in RANGES:
        raise ValueError("invalid range")
    end = end or today_utc()
    days = RANGES[range_key]
    if days is None:
        first = db.session.execute(
            text("SELECT min(CAST(created_at AS date)) FROM users")
        ).scalar()
        start = max(first or end, end - timedelta(days=MAX_ALL_DAYS - 1))
    else:
        start = end - timedelta(days=days - 1)
    return start, end


def _granularity(start: date, end: date) -> str:
    return "day" if (end - start).days < 90 else "week"


def _bucket_expr(date_expr: str, granularity: str) -> str:
    if granularity == "week":
        return f"CAST(date_trunc('week', {date_expr}) AS date)"
    return f"CAST({date_expr} AS date)"


def _bucket_keys(start: date, end: date, granularity: str):
    if granularity == "day":
        current, step = start, timedelta(days=1)
    else:
        current, step = start - timedelta(days=start.weekday()), timedelta(days=7)
    keys = []
    while current <= end:
        keys.append(current)
        current += step
    return keys


def _dense(rows, keys):
    by_key = {row[0]: int(row[1]) for row in rows}
    return [{"date": key.isoformat(), "value": by_key.get(key, 0)} for key in keys]


def _scalar(sql: str, **params):
    return db.session.execute(text(sql), params).scalar() or 0


# --- Users ------------------------------------------------------------------------


def users_section(start: date, end: date, granularity: str):
    start_dt, end_dt = _start_of(start), _start_of(end + timedelta(days=1))
    total = _scalar("SELECT count(*) FROM users")
    new = _scalar(
        "SELECT count(*) FROM users WHERE created_at >= :s AND created_at < :e",
        s=start_dt,
        e=end_dt,
    )
    bucket = _bucket_expr("created_at", granularity)
    rows = db.session.execute(
        text(
            f"SELECT {bucket} AS b, count(*) FROM users "
            "WHERE created_at >= :s AND created_at < :e GROUP BY b ORDER BY b"
        ),
        {"s": start_dt, "e": end_dt},
    ).all()
    return {
        "total": int(total),
        "new_in_period": int(new),
        "premium": int(_scalar("SELECT count(*) FROM users WHERE is_premium IS TRUE")),
        "with_telegram": int(_scalar("SELECT count(*) FROM telegram_identities")),
        "registrations": _dense(rows, _bucket_keys(start, end, granularity)),
    }


# --- Feature usage (history) -------------------------------------------------------


def _feature_totals(table, user_col, date_expr, where, s, e, previous=None):
    """(records, distinct users) in [s, e], plus records in the ``previous``
    (start, end) window, or None without one."""
    if previous is None:
        row = db.session.execute(
            text(
                f"SELECT count(*), count(DISTINCT {user_col}) FROM {table} "
                f"WHERE {where} AND {date_expr} BETWEEN :s AND :e"
            ),
            {"s": s, "e": e},
        ).one()
        return int(row[0]), int(row[1]), None
    ps, pe = previous
    row = db.session.execute(
        text(
            f"""
            SELECT
              count(*) FILTER (WHERE {date_expr} BETWEEN :s AND :e),
              count(DISTINCT {user_col}) FILTER (WHERE {date_expr} BETWEEN :s AND :e),
              count(*) FILTER (WHERE {date_expr} BETWEEN :ps AND :pe)
            FROM {table}
            WHERE {where} AND {date_expr} BETWEEN :ps AND :e
            """
        ),
        {"s": s, "e": e, "ps": ps, "pe": pe},
    ).one()
    return int(row[0]), int(row[1]), int(row[2])


def features_section(start: date, end: date, granularity: str, compare: bool):
    span = (end - start).days + 1
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=span - 1)
    keys = _bucket_keys(start, end, granularity)
    features = []
    union_parts = []
    for key, (label, table, user_col, date_expr, where) in FEATURES.items():
        records, users, previous = _feature_totals(
            table,
            user_col,
            date_expr,
            where,
            start,
            end,
            (prev_start, prev_end) if compare else None,
        )
        bucket = _bucket_expr(date_expr, granularity)
        rows = db.session.execute(
            text(
                f"SELECT {bucket} AS b, count(*) FROM {table} "
                f"WHERE {where} AND {date_expr} BETWEEN :s AND :e GROUP BY b ORDER BY b"
            ),
            {"s": start, "e": end},
        ).all()
        trend = None
        if compare and previous >= MIN_PREVIOUS_RECORDS:
            change = (records - previous) / previous
            trend = (
                "declining"
                if change <= -TREND_THRESHOLD
                else "growing" if change >= TREND_THRESHOLD else "stable"
            )
        features.append(
            {
                "key": key,
                "label": label,
                "records": records,
                "users": users,
                "records_per_user": round(records / users, 2) if users else None,
                "previous_records": previous,
                "trend": trend,
                "series": _dense(rows, keys),
            }
        )
        union_parts.append(
            f"SELECT {user_col} AS u FROM {table} "
            f"WHERE {where} AND {date_expr} BETWEEN :s AND :e"
        )
    users_any = int(
        db.session.execute(
            text(
                "SELECT count(DISTINCT u) FROM (" + " UNION ALL ".join(union_parts) + ") x"
            ),
            {"s": start, "e": end},
        ).scalar()
        or 0
    )
    for feature in features:
        feature["reach"] = (
            round(feature["users"] / users_any, 4) if users_any else None
        )
    return {"users_with_any_record": users_any, "items": features}


# --- Tracked activity ---------------------------------------------------------------


def _distinct_users(since: date, until: date) -> int:
    return int(
        _scalar(
            "SELECT count(DISTINCT user_id) FROM activity_events "
            "WHERE day BETWEEN :s AND :e",
            s=since,
            e=until,
        )
    )


def tracked_section(start: date, end: date, granularity: str):
    tracking_since = db.session.execute(
        text("SELECT min(day) FROM activity_events")
    ).scalar()
    if tracking_since is None:
        return {"available": False, "tracking_since": None}

    dau = _distinct_users(end, end)
    wau = _distinct_users(end - timedelta(days=6), end)
    mau = _distinct_users(end - timedelta(days=29), end)

    keys = _bucket_keys(start, end, granularity)
    bucket = _bucket_expr("day", granularity)
    daily = db.session.execute(
        text(
            f"SELECT {bucket} AS b, count(DISTINCT user_id) FROM activity_events "
            "WHERE day BETWEEN :s AND :e GROUP BY b ORDER BY b"
        ),
        {"s": start, "e": end},
    ).all()

    period_users = _distinct_users(start, end)
    new_users, returning, unknown = new_and_returning(start, end, tracking_since)
    user_days = int(
        _scalar(
            "SELECT count(*) FROM (SELECT DISTINCT user_id, day FROM activity_events "
            "WHERE day BETWEEN :s AND :e) x",
            s=start,
            e=end,
        )
    )
    by_source = {
        row[0]: int(row[1])
        for row in db.session.execute(
            text(
                "SELECT source, count(DISTINCT user_id) FROM activity_events "
                "WHERE day BETWEEN :s AND :e GROUP BY source"
            ),
            {"s": start, "e": end},
        )
    }
    by_event = [
        {"event": row[0], "users": int(row[1]), "user_days": int(row[2])}
        for row in db.session.execute(
            text(
                "SELECT event, count(DISTINCT user_id), count(*) FROM ("
                "SELECT DISTINCT user_id, day, event FROM activity_events "
                "WHERE day BETWEEN :s AND :e) x GROUP BY event ORDER BY event"
            ),
            {"s": start, "e": end},
        )
    ]
    return {
        "available": True,
        "tracking_since": tracking_since.isoformat(),
        "covers_whole_period": tracking_since <= start,
        "dau": dau,
        "wau": wau,
        "mau": mau,
        "active_users_in_period": period_users,
        # new + returning + unknown == active_users_in_period
        "new": new_users,
        "returning": returning,
        "unknown": unknown,
        "avg_active_days_per_user": (
            round(user_days / period_users, 2) if period_users else None
        ),
        "active_users_by_source": by_source,
        "events": by_event,
        "active_series": _dense(daily, keys),
        "retention": retention(start, end, tracking_since),
    }


def new_and_returning(start: date, end: date, tracking_since: date):
    """Split the users active in [start, end] into (new, returning, unknown).

    returning: tracked activity before ``start`` (exact).
    new: no earlier tracked activity and registered on or after the day
         tracking began, so the whole history is tracked (exact).
    unknown: no earlier tracked activity but registered before tracking
         began: they may have been active before it, which is not recorded.
    """
    row = db.session.execute(
        text(
            """
            SELECT
              count(*) FILTER (WHERE NOT earlier AND created_at >= :since),
              count(*) FILTER (WHERE earlier),
              count(*) FILTER (WHERE NOT earlier AND created_at < :since)
            FROM (
              SELECT u.created_at, EXISTS (
                SELECT 1 FROM activity_events a
                WHERE a.user_id = p.user_id AND a.day < :s
              ) AS earlier
              FROM (
                SELECT DISTINCT user_id FROM activity_events
                WHERE day BETWEEN :s AND :e
              ) p
              JOIN users u ON u.id = p.user_id
            ) x
            """
        ),
        {"s": start, "e": end, "since": _start_of(tracking_since)},
    ).one()
    return int(row[0]), int(row[1]), int(row[2])


def retention(start: date, end: date, tracking_since: date):
    """Day-N retention of users whose first activity falls in [start, end].

    Cohort: users who registered on or after the day tracking began (so their
    first tracked day really is their first activity) and whose first activity
    day D0 is in the period. Day-N retained: active again on exactly D0+N.
    Only cohort members with D0+N <= end are counted ("matured"). Also
    ``returned``: cohort members with activity on any later day.
    """
    since_dt = _start_of(tracking_since)
    cte = """
        WITH cohort AS (
          SELECT e.user_id, min(e.day) AS d0
          FROM activity_events e
          JOIN users u ON u.id = e.user_id
          WHERE u.created_at >= :since
          GROUP BY e.user_id
          HAVING min(e.day) BETWEEN :s AND :e
        )
    """
    result = {}
    for n in (1, 7, 30):
        row = db.session.execute(
            text(
                cte
                + """
                SELECT count(*),
                  count(*) FILTER (WHERE EXISTS (
                    SELECT 1 FROM activity_events a
                    WHERE a.user_id = cohort.user_id AND a.day = cohort.d0 + :n))
                FROM cohort WHERE cohort.d0 + :n <= :e
                """
            ),
            {"since": since_dt, "s": start, "e": end, "n": n},
        ).one()
        cohort, retained = int(row[0]), int(row[1])
        result[f"day{n}"] = {
            "cohort": cohort,
            "retained": retained,
            "rate": round(retained / cohort, 4) if cohort else None,
        }
    row = db.session.execute(
        text(
            cte
            + """
            SELECT count(*),
              count(*) FILTER (WHERE EXISTS (
                SELECT 1 FROM activity_events a
                WHERE a.user_id = cohort.user_id AND a.day > cohort.d0))
            FROM cohort
            """
        ),
        {"since": since_dt, "s": start, "e": end},
    ).one()
    cohort, returned = int(row[0]), int(row[1])
    result["returned"] = {
        "cohort": cohort,
        "returned": returned,
        "rate": round(returned / cohort, 4) if cohort else None,
    }
    return result


# --- Entry point --------------------------------------------------------------------


def build_analytics(range_key: str, end: date | None = None) -> dict:
    start, end = resolve_range(range_key, end)
    granularity = _granularity(start, end)
    compare = RANGES[range_key] is not None
    return {
        "range": range_key,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "granularity": granularity,
        "timezone": "UTC",
        "users": users_section(start, end, granularity),
        "features": features_section(start, end, granularity, compare),
        "tracked": tracked_section(start, end, granularity),
    }
