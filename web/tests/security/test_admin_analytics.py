"""Admin analytics: access control, metric maths, tracking and its failure modes."""

from datetime import date, datetime, timedelta, timezone

import pytest
from flask import g
from werkzeug.security import generate_password_hash

from backend.app.extensions import db
from backend.app.models.activity_event import ActivityEvent
from backend.app.models.nutrition.meal import Meal
from backend.app.models.nutrition.user_water import UserWater
from backend.app.models.user import User
from backend.app.services.analytics import build_analytics, resolve_range
from backend.app.utils.admin import is_admin, parse_admin_emails
from web.app import activity

PASSWORD = "password123"
ADMIN_EMAIL = "boss@example.com"
END = date(2026, 6, 30)


@pytest.fixture(autouse=True)
def _fresh_tracker():
    activity._seen.clear()
    activity._purged_on["day"] = None
    yield
    activity._seen.clear()
    activity._purged_on["day"] = None


def _login(client, email, password=PASSWORD):
    response = client.post("/auth/login", data={"email": email, "password": password})
    g.pop("_login_user", None)
    return response


def _make_user(name, email, created=None):
    u = User(
        username=name,
        email=email,
        password=generate_password_hash(PASSWORD),
        created_at=created or datetime(2026, 6, 1),
    )
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def admin(app):
    app.config["ADMIN_EMAILS"] = f"  {ADMIN_EMAIL.upper()} , other@example.com;\n"
    return _make_user("boss", ADMIN_EMAIL)


@pytest.fixture
def admin_client(app, admin):
    client = app.test_client()
    _login(client, ADMIN_EMAIL)
    return client


def _get(client, path):
    g.pop("_login_user", None)
    return client.get(path)


# --- ADMIN_EMAILS parsing ----------------------------------------------------------


def test_admin_email_parsing():
    assert parse_admin_emails(" A@x.com, b@y.com;\nc@z.com ") == {
        "a@x.com",
        "b@y.com",
        "c@z.com",
    }
    for empty in (None, "", "   ", ",;", 5, "no-at-sign"):
        assert parse_admin_emails(empty) == frozenset()


def test_is_admin_requires_listing_and_authentication(app):
    class Fake:
        is_authenticated = True
        email = "Boss@Example.com"

    assert is_admin(Fake(), "boss@example.com")
    assert not is_admin(Fake(), "")
    assert not is_admin(Fake(), None)
    assert not is_admin(None, "boss@example.com")
    Fake.is_authenticated = False
    assert not is_admin(Fake(), "boss@example.com")


# --- Access control ----------------------------------------------------------------


@pytest.mark.parametrize("path", ["/admin/analytics", "/admin/analytics/data"])
def test_anonymous_is_rejected(client, path):
    response = client.get(path)
    assert response.status_code in (302, 401)
    if response.status_code == 302:
        assert "/auth/login" in response.location


def test_ordinary_user_gets_404(app, user):
    app.config["ADMIN_EMAILS"] = ADMIN_EMAIL
    client = app.test_client()
    _login(client, "test@example.com")

    assert _get(client, "/admin/analytics").status_code == 404
    assert _get(client, "/admin/analytics/data").status_code == 404


def test_nobody_is_admin_when_variable_is_empty_or_missing(app, admin):
    for value in ("", None, "   "):
        app.config["ADMIN_EMAILS"] = value
        client = app.test_client()
        _login(client, ADMIN_EMAIL)
        assert _get(client, "/admin/analytics").status_code == 404
        assert _get(client, "/admin/analytics/data").status_code == 404


def test_admin_can_open_page_and_data(admin_client):
    page = _get(admin_client, "/admin/analytics")
    assert page.status_code == 200
    assert page.headers["Cache-Control"] == "no-store"
    assert b"noindex" in page.data

    data = _get(admin_client, "/admin/analytics/data?range=30")
    assert data.status_code == 200
    assert data.headers["Cache-Control"] == "no-store"
    body = data.get_json()
    assert set(body) >= {"users", "features", "tracked", "start", "end"}


def test_admin_telegram_session_is_not_enough(app, admin):
    client = app.test_client()
    _login(client, ADMIN_EMAIL)
    with client.session_transaction() as session:
        session["tg_identity"] = 1

    assert _get(client, "/admin/analytics/data").status_code != 200


@pytest.mark.parametrize("value", ["", "1", "365", "-7", "abc", "7;DROP", "30 ", "ALL"])
def test_invalid_range_is_rejected(admin_client, value):
    response = _get(admin_client, f"/admin/analytics/data?range={value}")
    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid_range"


@pytest.mark.parametrize("value", ["7", "30", "90", "all"])
def test_valid_ranges(admin_client, value):
    assert _get(admin_client, f"/admin/analytics/data?range={value}").status_code == 200


# --- Metric maths -----------------------------------------------------------------


def test_empty_database_is_handled(app):
    result = build_analytics("30", end=END)

    assert result["users"]["total"] == 0
    assert result["users"]["new_in_period"] == 0
    assert len(result["users"]["registrations"]) == 30
    assert result["tracked"] == {"available": False, "tracking_since": None}
    assert all(f["records"] == 0 and f["users"] == 0 for f in result["features"]["items"])
    assert all(f["records_per_user"] is None for f in result["features"]["items"])


def test_range_bounds():
    assert resolve_range("7", END) == (END - timedelta(days=6), END)
    assert resolve_range("90", END)[0] == END - timedelta(days=89)
    with pytest.raises(ValueError):
        resolve_range("14", END)


def test_user_and_registration_counts(app):
    _make_user("a", "a@example.com", datetime(2026, 6, 30, 23, 59))
    _make_user("b", "b@example.com", datetime(2026, 6, 30, 0, 0))
    _make_user("c", "c@example.com", datetime(2026, 6, 23, 12, 0))  # before the 7 d window
    _make_user("d", "d@example.com", datetime(2026, 7, 1, 0, 0))  # after the end

    users = build_analytics("7", end=END)["users"]

    assert users["total"] == 4
    assert users["new_in_period"] == 2
    assert sum(p["value"] for p in users["registrations"]) == 2
    assert users["registrations"][-1] == {"date": "2026-06-30", "value": 2}


def test_feature_records_are_not_users(app):
    u1 = _make_user("a", "a@example.com")
    u2 = _make_user("b", "b@example.com")
    for day in (28, 29, 30):
        db.session.add(Meal(user_id=u1.id, date=date(2026, 6, day), name="x", category="lunch"))
    db.session.add(Meal(user_id=u2.id, date=date(2026, 6, 30), name="y", category="lunch"))
    db.session.add(Meal(user_id=u2.id, date=date(2026, 5, 1), name="old", category="lunch"))
    db.session.add(UserWater(user_id=u1.id, date=date(2026, 6, 30), amount=1.0))
    db.session.commit()

    features = {f["key"]: f for f in build_analytics("7", end=END)["features"]["items"]}
    food = features["food"]

    assert food["records"] == 4
    assert food["users"] == 2
    assert food["records_per_user"] == 2.0
    assert sum(p["value"] for p in food["series"]) == 4
    assert features["water"]["records"] == 1 and features["water"]["users"] == 1
    # reach: 2 of the 2 users with any record
    assert food["reach"] == 1.0 and features["water"]["reach"] == 0.5


def test_feature_trend_against_previous_period(app):
    u = _make_user("a", "a@example.com")
    for i in range(10):  # previous 7 days: 10 meals
        db.session.add(Meal(user_id=u.id, date=END - timedelta(days=7 + i % 7), name="x", category="c"))
    db.session.add(Meal(user_id=u.id, date=END, name="x", category="c"))  # now: 1
    db.session.commit()

    food = next(f for f in build_analytics("7", end=END)["features"]["items"] if f["key"] == "food")

    assert food["previous_records"] == 10
    assert food["trend"] == "declining"


def _events(user, *days, event="food", source="web"):
    for day in days:
        db.session.add(ActivityEvent(user_id=user.id, day=day, event=event, source=source))
    db.session.commit()


def test_active_users_dau_wau_mau(app):
    users = [_make_user(f"u{i}", f"u{i}@example.com") for i in range(4)]
    _events(users[0], END, END - timedelta(days=3))
    _events(users[1], END - timedelta(days=6))
    _events(users[2], END - timedelta(days=20))
    _events(users[3], END - timedelta(days=40))

    tracked = build_analytics("90", end=END)["tracked"]

    assert tracked["available"] is True
    assert (tracked["dau"], tracked["wau"], tracked["mau"]) == (1, 2, 3)
    assert tracked["active_users_in_period"] == 4
    assert sum(p["value"] for p in tracked["active_series"]) > 0


def test_events_are_deduplicated_per_user_day_event_source(app):
    u = _make_user("a", "a@example.com")
    _events(u, END)
    _events(u, END, event="water")  # same day, other event: still one active user
    tracked = build_analytics("7", end=END)["tracked"]

    assert tracked["dau"] == 1
    assert tracked["avg_active_days_per_user"] == 1.0
    with pytest.raises(Exception):  # duplicate primary key
        _events(u, END)
    db.session.rollback()


def test_new_versus_returning_users(app):
    # Tracking starts on END-60 (the earliest event); both registered after it.
    old = _make_user("old", "old@example.com")
    new = _make_user("new", "new@example.com")
    _events(old, END - timedelta(days=60), END)
    _events(new, END - timedelta(days=1))

    tracked = build_analytics("7", end=END)["tracked"]

    assert tracked["active_users_in_period"] == 2
    assert (tracked["new"], tracked["returning"], tracked["unknown"]) == (1, 1, 0)


def test_user_registered_before_tracking_is_not_called_new(app):
    launch = END - timedelta(days=30)
    anchor = _make_user("anchor", "anchor@example.com", datetime(2026, 1, 1))
    _events(anchor, launch)  # tracking began on `launch`
    # Registered long before tracking; first tracked action is in the period:
    # they may well have used the app before, so this is not knowable.
    legacy = _make_user("legacy", "legacy@example.com", datetime(2026, 1, 1))
    _events(legacy, END)
    # Registered before tracking, but tracked activity before the period: returning.
    regular = _make_user("regular", "regular@example.com", datetime(2026, 1, 1))
    _events(regular, launch + timedelta(days=1), END)
    # Registered after tracking began, first action in the period: new.
    fresh = _make_user("fresh", "fresh@example.com", datetime.combine(END, datetime.min.time()))
    _events(fresh, END)

    tracked = build_analytics("7", end=END)["tracked"]

    assert tracked["active_users_in_period"] == 3
    assert (tracked["new"], tracked["returning"], tracked["unknown"]) == (1, 1, 1)
    assert tracked["new"] + tracked["returning"] + tracked["unknown"] == 3


def test_retention_follows_cohort_definition(app):
    end = date(2026, 7, 5)
    d0 = date(2026, 6, 1)  # the first tracked day
    stay = _make_user("stay", "stay@example.com", datetime(2026, 6, 1))
    leave = _make_user("leave", "leave@example.com", datetime(2026, 6, 1))
    late = _make_user("late", "late@example.com", datetime(2026, 7, 5))
    legacy = _make_user("legacy", "legacy@example.com", datetime(2026, 1, 1))
    _events(stay, d0, d0 + timedelta(days=1), d0 + timedelta(days=7), d0 + timedelta(days=30))
    _events(leave, d0)
    _events(late, end)  # D1 would be after the end: not matured, not counted
    _events(legacy, d0)  # registered before tracking began: not in any cohort

    retention = build_analytics("all", end=end)["tracked"]["retention"]

    assert retention["day1"] == {"cohort": 2, "retained": 1, "rate": 0.5}
    assert retention["day7"] == {"cohort": 2, "retained": 1, "rate": 0.5}
    assert retention["day30"] == {"cohort": 2, "retained": 1, "rate": 0.5}
    # "returned" looks at any later day and includes the not yet matured user
    assert retention["returned"] == {"cohort": 3, "returned": 1, "rate": round(1 / 3, 4)}


def test_events_outside_period_are_ignored(app):
    u = _make_user("a", "a@example.com")
    _events(u, END - timedelta(days=100))

    tracked = build_analytics("7", end=END)["tracked"]

    assert tracked["available"] is True
    assert tracked["active_users_in_period"] == 0
    assert tracked["avg_active_days_per_user"] is None


def test_response_contains_no_personal_data(app, admin_client, user):
    _events(user, date.today())
    body = _get(admin_client, "/admin/analytics/data?range=all").get_data(as_text=True)

    for secret in ("test@example.com", "testuser", ADMIN_EMAIL, "boss", "password"):
        assert secret not in body


# --- Tracking hook ----------------------------------------------------------------


def _rows():
    db.session.expire_all()
    return ActivityEvent.query.all()


def _post_water(client, amount=0.5):
    g.pop("_login_user", None)
    return client.post("/api/nutrition/water", json={"amount": amount})


def test_successful_action_is_tracked_once_per_day(client, user):
    _login(client, "test@example.com")

    assert _post_water(client).status_code == 200
    assert _post_water(client).status_code == 200

    rows = _rows()
    assert [(r.user_id, r.event, r.source, r.day) for r in rows] == [
        (user.id, "water", "web", datetime.utcnow().date())
    ]


def test_reads_failures_and_anonymous_requests_are_not_tracked(client, user):
    assert client.post("/api/nutrition/water", json={"amount": 1}).status_code == 401
    _login(client, "test@example.com")
    g.pop("_login_user", None)
    client.get("/api/nutrition/water")
    client.get("/dashboard/")
    assert _post_water(client, amount=999).status_code == 400

    assert _rows() == []


def test_tracking_can_be_switched_off(app, client, user):
    app.config["ACTIVITY_TRACKING"] = False
    _login(client, "test@example.com")

    assert _post_water(client).status_code == 200
    assert _rows() == []


def test_tracker_failure_never_breaks_the_request(app, client, user, monkeypatch):
    _login(client, "test@example.com")

    # Executing a plain string raises inside the tracker's own connection.
    monkeypatch.setattr(activity, "_INSERT", "not executable")

    response = _post_water(client)

    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_events_are_removed_with_the_user(app):
    u = _make_user("gone", "gone@example.com")
    _events(u, END)
    uid = u.id

    db.session.delete(u)
    db.session.commit()

    assert ActivityEvent.query.filter_by(user_id=uid).count() == 0


# --- Every feature, every range (independently counted) ---------------------------


def _seed_all_features():
    """Records of all six features at known dates; returns {feature: [(user_id, day)]}.

    Dates span ~200 days before END plus one future day, and timestamps sit on
    day boundaries, so range edges and the date casts are exercised.
    """
    from backend.app.models.nutrition.user_weight import UserWeight
    from backend.app.models.recovery.habit import RecoveryHabit
    from backend.app.models.recovery.habit_log import RecoveryHabitLog
    from backend.app.models.recovery.sleep_entry import SleepEntry
    from backend.app.models.recovery.user_habit import UserRecoveryHabit
    from backend.app.models.training_session import TrainingSession

    users = [_make_user(f"f{i}", f"f{i}@example.com", datetime(2025, 12, 1)) for i in range(4)]
    offsets = [0, 1, 6, 7, 29, 30, 89, 90, 200, -1]  # days before END; -1 = tomorrow
    habit = RecoveryHabit(slug="walk", name="Walk", points=5)
    db.session.add(habit)
    db.session.flush()
    expected = {k: [] for k in ("food", "water", "weight", "training", "sleep", "habits")}
    for n, user in enumerate(users):
        user_habit = UserRecoveryHabit(user_id=user.id, habit_id=habit.id)
        db.session.add(user_habit)
        db.session.flush()
        for offset in offsets[n:]:  # each user has a different share of the dates
            day = END - timedelta(days=offset)
            edge = datetime.combine(day, datetime.min.time())
            late = edge + timedelta(hours=23, minutes=59, seconds=59)
            db.session.add(Meal(user_id=user.id, date=day, name="m", category="c"))
            db.session.add(Meal(user_id=user.id, date=day, name="m2", category="c"))
            db.session.add(UserWater(user_id=user.id, date=day, amount=1.0))
            db.session.add(UserWeight(user_id=user.id, date=day, weight=70.0))
            db.session.add(TrainingSession(user_id=user.id, started_at=late, status="done"))
            db.session.add(
                SleepEntry(
                    user_id=user.id,
                    sleep_start=edge.replace(tzinfo=timezone.utc) - timedelta(hours=8),
                    sleep_end=edge.replace(tzinfo=timezone.utc),
                    duration_minutes=480,
                    quality_score=80,
                    created_at=late.replace(tzinfo=timezone.utc),
                )
            )
            db.session.add(
                RecoveryHabitLog(
                    user_habit_id=user_habit.id,
                    user_id=user.id,
                    date=day,
                    completed=True,
                    completed_at=edge.replace(tzinfo=timezone.utc),
                )
            )
            expected["food"] += [(user.id, day), (user.id, day)]
            for key in ("water", "weight", "training", "sleep", "habits"):
                expected[key].append((user.id, day))
        # Not completed / no timestamp: never counted as a done habit.
        db.session.add(
            RecoveryHabitLog(
                user_habit_id=user_habit.id,
                user_id=user.id,
                date=END - timedelta(days=400),
                completed=False,
            )
        )
    db.session.add(TrainingSession(user_id=None, started_at=None, status="planned"))
    db.session.commit()
    return expected


@pytest.mark.parametrize("range_key", ["7", "30", "90", "all"])
def test_every_feature_matches_an_independent_count(app, range_key):
    expected = _seed_all_features()
    result = build_analytics(range_key, end=END)
    start, end = date.fromisoformat(result["start"]), date.fromisoformat(result["end"])
    features = {f["key"]: f for f in result["features"]["items"]}
    assert set(features) == set(expected)

    in_range = {k: [(u, d) for u, d in rows if start <= d <= end] for k, rows in expected.items()}
    any_users = {u for rows in in_range.values() for u, _ in rows}
    assert result["features"]["users_with_any_record"] == len(any_users)

    for key, rows in in_range.items():
        feature = features[key]
        users = {u for u, _ in rows}
        assert feature["records"] == len(rows), key
        assert feature["users"] == len(users), key
        assert sum(p["value"] for p in feature["series"]) == feature["records"], key
        assert feature["reach"] == (round(len(users) / len(any_users), 4) if any_users else None), key
        assert feature["records_per_user"] == (round(len(rows) / len(users), 2) if users else None)
        if range_key == "all":
            assert feature["records"] > 0, key  # B1: "all" used to report zero
            assert feature["previous_records"] is None and feature["trend"] is None


def test_all_range_reports_records_of_the_whole_history(app):
    u = _make_user("a", "a@example.com", datetime(2025, 1, 1))
    db.session.add(Meal(user_id=u.id, date=date(2025, 1, 2), name="x", category="c"))
    db.session.add(Meal(user_id=u.id, date=END, name="x", category="c"))
    db.session.commit()

    food = next(f for f in build_analytics("all", end=END)["features"]["items"] if f["key"] == "food")

    assert (food["records"], food["users"], food["reach"]) == (2, 1, 1.0)


# --- Dates of timestamptz columns do not depend on the session time zone ----------


def test_sleep_and_habit_days_are_utc_in_any_session_time_zone(app):
    from sqlalchemy import text

    from backend.app.models.recovery.habit import RecoveryHabit
    from backend.app.models.recovery.habit_log import RecoveryHabitLog
    from backend.app.models.recovery.sleep_entry import SleepEntry
    from backend.app.models.recovery.user_habit import UserRecoveryHabit

    u = _make_user("tz", "tz@example.com")
    habit = RecoveryHabit(slug="walk", name="Walk", points=5)
    db.session.add(habit)
    db.session.flush()
    user_habit = UserRecoveryHabit(user_id=u.id, habit_id=habit.id)
    db.session.add(user_habit)
    db.session.flush()
    # 22:30 UTC on END is already the next day in Kyiv (UTC+3 in summer).
    late_utc = datetime(2026, 6, 30, 22, 30, tzinfo=timezone.utc)
    db.session.add(
        SleepEntry(
            user_id=u.id,
            sleep_start=late_utc - timedelta(hours=8),
            sleep_end=late_utc,
            duration_minutes=480,
            quality_score=80,
            created_at=late_utc,
        )
    )
    db.session.add(
        RecoveryHabitLog(
            user_habit_id=user_habit.id, user_id=u.id, date=END, completed=True, completed_at=late_utc
        )
    )
    db.session.commit()

    db.session.execute(text("SET LOCAL TIME ZONE 'Europe/Kyiv'"))
    try:
        # The session really is in Kyiv time: a plain cast moves to the next day.
        plain = db.session.execute(
            text("SELECT CAST(created_at AS date) FROM recovery_sleep_entries")
        ).scalar()
        assert plain == END + timedelta(days=1)

        features = {f["key"]: f for f in build_analytics("7", end=END)["features"]["items"]}
    finally:
        db.session.rollback()

    for key in ("sleep", "habits"):
        assert features[key]["records"] == 1, key
        assert features[key]["series"][-1] == {"date": END.isoformat(), "value": 1}, key


# --- Tracking: every tracked endpoint, both API prefixes ---------------------------

# Mutating endpoints of the tracked blueprints that deliberately do NOT count
# as activity (edits, deletions, catalogue and plan management). A new
# endpoint must be added to TRACKED_ENDPOINTS or here, never forgotten.
NOT_TRACKED = {
    "nutrition_api.api_barcode_import",
    "nutrition_api.api_create_dish",
    "nutrition_api.api_create_product",
    "nutrition_api.api_delete_dish",
    "nutrition_api.api_delete_entry",
    "nutrition_api.api_delete_item",
    "nutrition_api.api_delete_meal",
    "nutrition_api.api_delete_product",
    "nutrition_api.api_edit_item",
    "nutrition_api.api_edit_meal",
    "nutrition_api.api_favorite_product",
    "nutrition_api.api_update_dish",
    "nutrition_api.api_update_entry",
    "nutrition_api.api_update_product",
    "recovery.add_habit",
    "recovery.remove_habit",
    "recovery.unlog_habit",
    "training_api.create_plan",
    "training_api.delete_plan",
    "training_api.strength_test",
    "training_api.update_plan",
    "training_api.update_session_exercise",
    "training_dashboard_api.add_exercise",
    "training_dashboard_api.update_exercise",
}
TRACKED_BLUEPRINTS = {"nutrition_api", "training_api", "training_dashboard_api", "recovery"}


def _rules_for(app, endpoint):
    return [r for r in app.url_map.iter_rules() if r.endpoint == endpoint]


def _sample_url(rule):
    values = {name: (1 if name.endswith("_id") or name == "habit_id" else "x") for name in rule.arguments}
    return rule.build(values, append_unknown=False)[1]


def test_canonical_endpoint():
    assert activity.canonical_endpoint("nutrition_api_v1.api_add_water") == "nutrition_api.api_add_water"
    assert activity.canonical_endpoint("nutrition_api.api_add_water") == "nutrition_api.api_add_water"
    assert activity.canonical_endpoint("static") == "static"
    # "_v1" only counts at the end of the blueprint part.
    assert activity.canonical_endpoint("x.view_v1") == "x.view_v1"


@pytest.mark.parametrize("endpoint", sorted(activity.TRACKED_ENDPOINTS))
@pytest.mark.parametrize("version", ["", "_v1"])
def test_every_tracked_endpoint_is_recognised_on_both_prefixes(app, endpoint, version):
    blueprint, view = endpoint.split(".")
    registered = f"{blueprint}{version}.{view}"
    rules = _rules_for(app, registered)
    assert rules, f"{registered} is not routed: tracking would silently stop"

    for rule in rules:
        method = sorted(rule.methods - {"GET", "HEAD", "OPTIONS"})[0]
        url = _sample_url(rule)
        assert url.startswith("/api/v1/" if version else "/api/") and (
            version or not url.startswith("/api/v1/")
        )
        with app.test_request_context(url, method=method):
            assert activity._event_for_request() == activity.TRACKED_ENDPOINTS[endpoint]
        with app.test_request_context(url, method="GET"):
            assert activity._event_for_request() is None


def test_no_mutating_endpoint_is_left_unclassified(app):
    unclassified = set()
    for rule in app.url_map.iter_rules():
        endpoint = activity.canonical_endpoint(rule.endpoint)
        blueprint = endpoint.split(".")[0]
        if blueprint not in TRACKED_BLUEPRINTS or not (rule.methods - {"GET", "HEAD", "OPTIONS"}):
            continue
        if endpoint not in activity.TRACKED_ENDPOINTS and endpoint not in NOT_TRACKED:
            unclassified.add(endpoint)
    assert unclassified == set()
    assert not (set(activity.TRACKED_ENDPOINTS) & NOT_TRACKED)


@pytest.mark.parametrize("endpoint", sorted(NOT_TRACKED))
def test_untracked_endpoints_record_nothing(app, endpoint):
    for rule in _rules_for(app, endpoint):
        method = sorted(rule.methods - {"GET", "HEAD", "OPTIONS"})[0]
        with app.test_request_context(_sample_url(rule), method=method):
            assert activity._event_for_request() is None


@pytest.mark.parametrize(
    "path, body, event",
    [
        ("/api/v1/nutrition/water", {"amount": 0.5}, "water"),
        ("/api/v1/nutrition/weight", {"weight": 70}, "weight"),
        ("/api/nutrition/weight", {"weight": 71}, "weight"),
    ],
)
def test_versioned_and_unversioned_requests_are_tracked(client, user, path, body, event):
    _login(client, "test@example.com")
    g.pop("_login_user", None)

    response = client.post(path, json=body)

    assert response.status_code == 200
    assert [(r.event, r.source) for r in _rows()] == [(event, "web")]


# --- Retention: 13 months ----------------------------------------------------------


def test_events_older_than_13_months_are_deleted_on_the_first_write_of_the_day(client, user):
    today = datetime.utcnow().date()
    keep = today - timedelta(days=activity.RETENTION_DAYS)  # exactly at the limit: kept
    drop = today - timedelta(days=activity.RETENTION_DAYS + 1)
    _events(user, keep, drop)
    activity._purged_on["day"] = None
    _login(client, "test@example.com")

    assert _post_water(client).status_code == 200

    days = sorted(r.day for r in _rows())
    assert drop not in days
    assert keep in days and today in days
    assert activity._purged_on["day"] == today


def test_purge_runs_once_per_day_per_process(client, user):
    today = datetime.utcnow().date()
    activity._purged_on["day"] = today  # already purged today in this process
    old = today - timedelta(days=activity.RETENTION_DAYS + 10)
    _events(user, old)
    _login(client, "test@example.com")

    assert _post_water(client).status_code == 200

    assert old in {r.day for r in _rows()}  # left for tomorrow's first write
