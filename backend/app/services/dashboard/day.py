from datetime import date

from .aggregator import _build_day


def get_day_details(user_id, day_iso):
    try:
        target_date = date.fromisoformat(day_iso)
    except (TypeError, ValueError):
        return None

    return _build_day(
        user_id,
        target_date,
    )

