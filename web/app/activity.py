"""Records "this user did X today" for the admin analytics.

Only a small allowlist of endpoints counts, and only when the request
succeeded: logging a meal, water, weight, a workout, sleep or a habit. Page
views, reads, background requests and failed requests never count. A row has
no content (no food, weights, text, IP or tokens), and each
(user, day, event, source) is written at most once per process thanks to an
in-memory set plus the table's primary key.

The write uses its own short connection with a lock timeout, after the
request has already been answered by the view, and swallows every error: a
broken or disabled tracker can never fail or slow down a user's request.
"""

from datetime import datetime, timezone

from flask import current_app, request
from flask_login import current_user
from sqlalchemy import text

from api import V1_SUFFIX
from auth.telegram_session import is_telegram_session
from backend.app.extensions import db

# endpoint -> event. Only creation/completion actions.
TRACKED_ENDPOINTS = {
    "nutrition_api.api_add_entry": "food",
    "nutrition_api.api_add_entries_bulk": "food",
    "nutrition_api.api_log_food": "food",
    "nutrition_api.api_add_meal": "food",
    "nutrition_api.api_add_item": "food",
    "nutrition_api.api_copy_yesterday": "food",
    "nutrition_api.api_add_water": "water",
    "nutrition_api.api_update_weight": "weight",
    "training_api.start_session": "workout",
    "training_api.complete_session": "workout",
    "training_api.finish_session": "workout",
    "training_dashboard_api.start_session": "workout",
    "training_dashboard_api.finish_session": "workout",
    "recovery.add_sleep": "sleep",
    "recovery.log_habit": "habit",
}

_INSERT = text(
    "INSERT INTO activity_events (user_id, day, event, source) "
    "VALUES (:user_id, :day, :event, :source) ON CONFLICT DO NOTHING"
)
_SEEN_LIMIT = 50_000
_seen: set = set()


def canonical_endpoint(endpoint: str) -> str:
    """"nutrition_api_v1.api_add_water" -> "nutrition_api.api_add_water".

    api.register_api registers each blueprint a second time for /api/v1/
    under the name ``<blueprint>_v1``, so the suffix belongs to the
    blueprint part of the endpoint, not to its end.
    """
    blueprint, dot, view = endpoint.partition(".")
    if not dot:
        return endpoint
    return f"{blueprint.removesuffix(V1_SUFFIX)}.{view}"


def _event_for_request():
    if request.method in ("GET", "HEAD", "OPTIONS") or not request.endpoint:
        return None
    return TRACKED_ENDPOINTS.get(canonical_endpoint(request.endpoint))


def record_activity(response):
    try:
        if not current_app.config.get("ACTIVITY_TRACKING") or response.status_code >= 400:
            return response
        event = _event_for_request()
        if event is None or not current_user.is_authenticated:
            return response

        user_id = current_user.id
        day = datetime.now(timezone.utc).date()
        source = "telegram" if is_telegram_session() else "web"
        key = (user_id, day, event, source)
        if key in _seen:
            return response

        with db.engine.begin() as connection:
            connection.execute(text("SET LOCAL lock_timeout = '1s'"))
            connection.execute(
                _INSERT,
                {"user_id": user_id, "day": day, "event": event, "source": source},
            )
        if len(_seen) >= _SEEN_LIMIT:
            _seen.clear()
        _seen.add(key)
    except Exception:  # tracking must never break the request
        current_app.logger.warning("Activity tracking failed", exc_info=False)
    return response


def init_activity_tracking(app):
    app.after_request(record_activity)
