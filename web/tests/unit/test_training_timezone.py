"""Training days follow the application clock (APP_TIMEZONE, utils/clock.py).

Sessions are stored as naive UTC. Which calendar day a session belongs to, what
"today" is for /today, the heatmap, the day details and plan completion, and
the dashboard's training history must all come from the same zone, also at
midnight, across zones and over daylight-saving changes.

Reference instants (Europe/Kyiv is UTC+3 until 25 Oct 2026, UTC+2 after;
Europe/Warsaw is one hour behind Kyiv):

    2026-10-13 21:30 UTC = Wed 14 Oct 00:30 Kyiv = Tue 13 Oct 23:30 Warsaw
"""

import datetime as dt

import pytest

from api.routes import training as routes
from backend.app.extensions import db
from backend.app.models.training_session import SessionExercise, TrainingSession
from backend.app.services.dashboard import aggregator
from backend.app.training.exercises.catalog import load_exercise_catalog
from backend.app.training.models.exercise import Exercise
from backend.app.utils import clock

UTC = dt.timezone.utc
AFTER_MIDNIGHT_KYIV = dt.datetime(2026, 10, 13, 21, 30)  # naive UTC


@pytest.fixture
def signed_in(client, user):
    client.post("/auth/login", data={"email": user.email, "password": "password123"})
    return client


@pytest.fixture
def library(app):
    for item in load_exercise_catalog():
        db.session.add(Exercise(**item))
    db.session.commit()
    return {row.slug: row for row in Exercise.query.all()}


def pin(monkeypatch, utc_moment, zone=None):
    """Make the application clock read ``utc_moment`` (naive UTC) in ``zone``."""
    if zone:
        monkeypatch.setenv("APP_TIMEZONE", zone)
    monkeypatch.setattr(
        clock, "now", lambda: utc_moment.replace(tzinfo=UTC).astimezone(clock.app_timezone())
    )


def add_session(user, library, started_utc):
    session = TrainingSession(
        user_id=user.id, started_at=started_utc, finished_at=started_utc, status="finished", internal_load=50
    )
    db.session.add(session)
    db.session.flush()
    db.session.add(SessionExercise(
        session_id=session.id, exercise_id=library["push-ups"].id, sets_done=3, reps_done="10"
    ))
    db.session.commit()
    return session


def heat(client, year=2026):
    days = client.get(f"/api/training/heatmap?year={year}").get_json()["days"]
    return {d["date"]: d for d in days}


def day_ids(client, day):
    return [s["session_id"] for s in client.get(f"/api/training/day/{day}").get_json()["sessions"]]


# --- the helpers read the application clock -----------------------------------------------


@pytest.mark.parametrize("zone, expected", [
    (None, dt.date(2026, 10, 14)),  # the default, Europe/Kyiv
    ("Europe/Kyiv", dt.date(2026, 10, 14)),
    ("Europe/Warsaw", dt.date(2026, 10, 13)),  # not hard-coded any more: it moves with APP_TIMEZONE
    ("America/New_York", dt.date(2026, 10, 13)),
    ("Pacific/Auckland", dt.date(2026, 10, 14)),
])
def test_today_and_session_dates_come_from_app_timezone(monkeypatch, zone, expected):
    pin(monkeypatch, AFTER_MIDNIGHT_KYIV, zone)

    assert routes._local_today() == expected
    assert routes._local_now().tzinfo is not None
    assert routes._local_date(AFTER_MIDNIGHT_KYIV) == expected
    assert routes._today_key() == ("wed" if expected.day == 14 else "tue")


def test_an_unknown_zone_falls_back_like_the_rest_of_the_application(monkeypatch):
    pin(monkeypatch, AFTER_MIDNIGHT_KYIV, "Not/AZone")

    assert routes._local_today() == dt.date(2026, 10, 14)


# --- /today, the heatmap, day details -----------------------------------------------------


def seed_week_plan(client, library):
    names = ["push-ups", "squat", "plank", "crunches", "glute-bridge", "lunges", "dead-bug"]
    days = {
        key: {"exercises": [{"exercise": {"id": library[name].id}, "sets": 3}]}
        for key, name in zip(["mon", "tue", "wed", "thu", "fri", "sat", "sun"], names)
    }
    client.post("/api/training/plans", json={"name": "Week", "is_active": True, "days": days})
    return {"tue": library["squat"].id, "wed": library["plank"].id}


@pytest.mark.parametrize("zone, weekday", [(None, "wed"), ("Europe/Warsaw", "tue")])
def test_today_picks_the_plan_day_of_the_local_date_at_midnight(signed_in, library, monkeypatch, zone, weekday):
    ids = seed_week_plan(signed_in, library)
    pin(monkeypatch, AFTER_MIDNIGHT_KYIV, zone)

    today = signed_in.get("/api/training/today").get_json()

    assert [e["exercise"]["id"] for e in today["exercises"]] == [ids[weekday]]


@pytest.mark.parametrize("zone, day", [(None, "2026-10-14"), ("Europe/Warsaw", "2026-10-13")])
def test_heatmap_and_day_details_put_a_session_on_its_local_day(signed_in, user, library, monkeypatch, zone, day):
    session = add_session(user, library, AFTER_MIDNIGHT_KYIV)
    pin(monkeypatch, AFTER_MIDNIGHT_KYIV, zone)
    other = "2026-10-13" if day == "2026-10-14" else "2026-10-14"

    heatmap = heat(signed_in)
    assert heatmap[day]["hard_sets"] > 0 and heatmap[other]["hard_sets"] == 0
    assert day_ids(signed_in, day) == [session.id]
    assert day_ids(signed_in, other) == []


def test_the_heatmap_year_defaults_to_the_local_year(signed_in, user, library, monkeypatch):
    # 22:30 UTC on 31 Dec is already 1 Jan in Kyiv, still the old year in UTC.
    pin(monkeypatch, dt.datetime(2026, 12, 31, 22, 30))

    days = signed_in.get("/api/training/heatmap").get_json()["days"]

    assert days[0]["date"] == "2027-01-01"
    assert [d for d in days if d["is_today"]][0]["date"] == "2027-01-01"


@pytest.mark.parametrize("zone, day", [("America/New_York", "2026-10-13"), ("Pacific/Auckland", "2026-10-14")])
def test_other_zones_move_the_day_boundary(signed_in, user, library, monkeypatch, zone, day):
    session = add_session(user, library, AFTER_MIDNIGHT_KYIV)
    pin(monkeypatch, AFTER_MIDNIGHT_KYIV, zone)

    assert day_ids(signed_in, day) == [session.id]


# --- daylight saving: 25-hour and 23-hour days ------------------------------------------------


def test_the_25_hour_day_when_clocks_go_back(signed_in, user, library, monkeypatch):
    # Kyiv, 25 Oct 2026: 04:00 EEST becomes 03:00 EET.
    pin(monkeypatch, dt.datetime(2026, 10, 26, 12, 0))
    before = add_session(user, library, dt.datetime(2026, 10, 24, 20, 30))  # 23:30 EEST, 24 Oct
    first = add_session(user, library, dt.datetime(2026, 10, 24, 21, 30))   # 00:30 EEST, 25 Oct
    last = add_session(user, library, dt.datetime(2026, 10, 25, 21, 30))    # 23:30 EET, 25 Oct
    after = add_session(user, library, dt.datetime(2026, 10, 25, 22, 30))   # 00:30 EET, 26 Oct

    assert sorted(day_ids(signed_in, "2026-10-25")) == sorted([first.id, last.id])
    assert day_ids(signed_in, "2026-10-24") == [before.id]
    assert day_ids(signed_in, "2026-10-26") == [after.id]
    days = heat(signed_in)
    assert [days[d]["hard_sets"] > 0 for d in ("2026-10-24", "2026-10-25", "2026-10-26")] == [True, True, True]
    assert routes._local_date(last.started_at) == dt.date(2026, 10, 25)
    assert routes._local_date(after.started_at) == dt.date(2026, 10, 26)


def test_the_23_hour_day_when_clocks_go_forward(signed_in, user, library, monkeypatch):
    # Kyiv, 29 Mar 2026: 03:00 EET becomes 04:00 EEST.
    pin(monkeypatch, dt.datetime(2026, 3, 30, 12, 0))
    first = add_session(user, library, dt.datetime(2026, 3, 28, 22, 0))   # 00:00 EET, 29 Mar
    last = add_session(user, library, dt.datetime(2026, 3, 29, 20, 59))   # 23:59 EEST, 29 Mar
    next_day = add_session(user, library, dt.datetime(2026, 3, 29, 21, 0))  # 00:00 EEST, 30 Mar
    previous = add_session(user, library, dt.datetime(2026, 3, 28, 21, 59))  # 23:59 EET, 28 Mar

    assert sorted(day_ids(signed_in, "2026-03-29")) == sorted([first.id, last.id])
    assert day_ids(signed_in, "2026-03-30") == [next_day.id]
    assert day_ids(signed_in, "2026-03-28") == [previous.id]


# --- the dashboard's training history ---------------------------------------------------------


@pytest.mark.parametrize("zone, day", [(None, dt.date(2026, 10, 14)), ("Europe/Warsaw", dt.date(2026, 10, 13))])
def test_dashboard_history_places_a_session_on_the_application_day(user, library, monkeypatch, zone, day):
    add_session(user, library, AFTER_MIDNIGHT_KYIV)
    pin(monkeypatch, AFTER_MIDNIGHT_KYIV, zone)

    assert aggregator.get_today_overview(user.id)["training"]["completed"] is True
    heatmap = {d["date"]: d for d in aggregator.get_heatmap(user.id)["days"]}
    done = [date for date, d in heatmap.items() if d["training"]["completed"]]
    assert done == [day.isoformat()]


def test_the_dashboard_day_after_midnight_does_not_still_show_yesterdays_session(user, library, monkeypatch):
    add_session(user, library, dt.datetime(2026, 10, 13, 20, 30))  # 23:30 Kyiv on the 13th
    pin(monkeypatch, AFTER_MIDNIGHT_KYIV)

    assert aggregator.get_today_overview(user.id)["training"]["completed"] is False
    assert aggregator._get_training_session(user.id, dt.date(2026, 10, 13)) is not None


# --- plan_date and completing a day ---------------------------------------------------------


def make_plan(client, library):
    entry = {"exercise": {"id": library["push-ups"].id}, "sets": 3, "reps": "10"}
    days = {key: {"exercises": [entry]} for key in ("mon", "tue", "wed", "thu", "fri")}
    return client.post("/api/training/plans", json={"name": "Week", "is_active": True, "days": days}).get_json()


def test_completing_a_day_just_after_midnight_counts_for_the_local_day_everywhere(
    signed_in, user, library, monkeypatch
):
    plan = make_plan(signed_in, library)
    pin(monkeypatch, AFTER_MIDNIGHT_KYIV)  # Wednesday 00:30 in Kyiv, still Tuesday in UTC

    done = signed_in.post(f"/api/training/plans/{plan['id']}/days/wed/complete").get_json()
    session = db.session.get(TrainingSession, done["session_id"])

    assert done["date"] == "2026-10-14" and session.plan_date == dt.date(2026, 10, 14)
    assert session.started_at == AFTER_MIDNIGHT_KYIV
    assert day_ids(signed_in, "2026-10-14") == [session.id]
    assert day_ids(signed_in, "2026-10-13") == []
    assert heat(signed_in)["2026-10-14"]["hard_sets"] > 0
    assert heat(signed_in)["2026-10-13"]["hard_sets"] == 0
    assert aggregator.get_today_overview(user.id)["training"]["completed"] is True
    week = {d["key"]: d for d in signed_in.get(f"/api/training/plans/{plan['id']}/week").get_json()["days"]}
    assert week["wed"]["completed"] is True and week["tue"]["completed"] is False
    again = signed_in.post(f"/api/training/plans/{plan['id']}/days/wed/complete").get_json()
    assert again["already_completed"] is True and TrainingSession.query.count() == 1


def test_the_same_instant_is_still_tuesday_in_a_zone_behind_kyiv(signed_in, library, monkeypatch):
    plan = make_plan(signed_in, library)
    pin(monkeypatch, AFTER_MIDNIGHT_KYIV, "Europe/Warsaw")  # Tuesday 23:30

    tue = signed_in.post(f"/api/training/plans/{plan['id']}/days/tue/complete")
    wed = signed_in.post(f"/api/training/plans/{plan['id']}/days/wed/complete")

    assert tue.status_code == 200 and tue.get_json()["date"] == "2026-10-13"
    assert (wed.status_code, wed.get_json()["code"]) == (409, "day_in_future")


def test_a_past_day_counts_on_its_own_date_in_any_zone(signed_in, user, library, monkeypatch):
    plan = make_plan(signed_in, library)
    pin(monkeypatch, dt.datetime(2026, 10, 15, 12, 0), "America/New_York")

    done = signed_in.post(f"/api/training/plans/{plan['id']}/days/mon/complete").get_json()

    assert done["date"] == "2026-10-12"
    assert day_ids(signed_in, "2026-10-12") == [done["session_id"]]  # noon local, never the day before or after
    assert day_ids(signed_in, "2026-10-11") == day_ids(signed_in, "2026-10-13") == []


def test_the_week_rolls_over_at_local_midnight_on_sunday(signed_in, library, monkeypatch):
    plan = make_plan(signed_in, library)
    sunday_late = dt.datetime(2026, 10, 18, 20, 30)  # 23:30 Kyiv, Sunday

    pin(monkeypatch, sunday_late)
    assert signed_in.get(f"/api/training/plans/{plan['id']}/week").get_json()["week_start"] == "2026-10-12"

    pin(monkeypatch, sunday_late + dt.timedelta(hours=1))  # 00:30 Kyiv, Monday: a new week
    week = signed_in.get(f"/api/training/plans/{plan['id']}/week").get_json()
    assert week["week_start"] == "2026-10-19" and week["days"][0]["is_today"] is True
