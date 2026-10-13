"""Recovery API: what test_critical_flows does not already cover."""

import datetime as dt

import pytest
from werkzeug.security import generate_password_hash

from backend.app.extensions import db
from backend.app.models.recovery.habit import RecoveryHabit
from backend.app.models.recovery.user_habit import UserRecoveryHabit
from backend.app.models.user import User

ROUTES = [
    ("post", "/api/recovery/sleep"),
    ("get", "/api/recovery/habits/list"),
    ("get", "/api/recovery/habits/user/1"),
    ("post", "/api/recovery/habits/add/1"),
    ("delete", "/api/recovery/habits/1"),
    ("post", "/api/recovery/habits/logs"),
    ("delete", "/api/recovery/habits/logs/1"),
    ("get", "/api/recovery/snapshot/1"),
    ("get", "/api/recovery/heatmap/1"),
    ("get", "/api/recovery/recommendations/1"),
    ("get", "/api/recovery/day-details/1"),
]


@pytest.fixture
def signed_in(client, user):
    client.post("/auth/login", data={"email": user.email, "password": "password123"})
    return client


@pytest.fixture
def habits(app):
    rows = {
        "walk": RecoveryHabit(slug="walk", name="Walk", points=5),
        "sauna": RecoveryHabit(slug="sauna", name="Sauna", points=5, premium_only=True),
        "old": RecoveryHabit(slug="old", name="Old", points=5, is_archived=True),
    }
    db.session.add_all(rows.values())
    db.session.commit()
    return rows


@pytest.mark.parametrize("method, path", ROUTES)
def test_guests_get_401(client, method, path):
    response = getattr(client, method)(path, json={})

    assert response.status_code == 401
    assert response.get_json() == {"error": "Authentication required"}


def test_premium_and_archived_habits_cannot_be_added(signed_in, habits):
    premium = signed_in.post(f"/api/recovery/habits/add/{habits['sauna'].id}")
    assert premium.status_code == 403
    assert premium.get_json() == {"error": "Premium required"}

    archived = signed_in.post(f"/api/recovery/habits/add/{habits['old'].id}")
    assert archived.status_code == 404
    assert archived.get_json() == {"error": "Not found"}

    assert UserRecoveryHabit.query.count() == 0


def test_adding_twice_reuses_the_habit(signed_in, habits):
    first = signed_in.post(f"/api/recovery/habits/add/{habits['walk'].id}").get_json()
    second = signed_in.post(f"/api/recovery/habits/add/{habits['walk'].id}").get_json()

    assert first["created"] is True
    assert second == {"created": False, "user_habit_id": first["user_habit_id"]}


def test_a_logged_habit_can_be_unlogged_and_removed(signed_in, user, habits):
    user_habit_id = signed_in.post(f"/api/recovery/habits/add/{habits['walk'].id}").get_json()["user_habit_id"]
    signed_in.post("/api/recovery/habits/logs", json={"user_habit_id": user_habit_id})

    unlogged = signed_in.delete(f"/api/recovery/habits/logs/{user_habit_id}")
    assert unlogged.status_code == 200
    assert unlogged.get_json() == {"removed": user_habit_id, "completed": False}
    listed = signed_in.get(f"/api/recovery/habits/user/{user.id}").get_json()
    assert [(h["slug"], h["completed"]) for h in listed] == [("walk", False)]

    removed = signed_in.delete(f"/api/recovery/habits/{user_habit_id}")
    assert removed.status_code == 200
    assert removed.get_json() == {"removed": user_habit_id}
    assert signed_in.get(f"/api/recovery/habits/user/{user.id}").get_json() == []


def test_other_users_habits_are_not_reachable(signed_in, habits):
    other = User(username="other", email="other@example.com", password=generate_password_hash("password123"))
    db.session.add(other)
    db.session.flush()
    foreign = UserRecoveryHabit(user_id=other.id, habit_id=habits["walk"].id, is_active=True)
    db.session.add(foreign)
    db.session.commit()

    for response in (
        signed_in.post("/api/recovery/habits/logs", json={"user_habit_id": foreign.id}),
        signed_in.delete(f"/api/recovery/habits/logs/{foreign.id}"),
        signed_in.delete(f"/api/recovery/habits/{foreign.id}"),
    ):
        assert response.status_code == 404
    assert db.session.get(UserRecoveryHabit, foreign.id) is not None


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"user_habit_id": "abc"},
    ],
)
def test_habit_log_needs_an_integer_id(signed_in, body):
    assert signed_in.post("/api/recovery/habits/logs", json=body).status_code == 400


@pytest.mark.parametrize(
    "start, end",
    [
        (None, "2026-01-02T07:00:00"),
        ("2026-01-02T07:00:00", "2026-01-01T23:00:00"),
        ("2026-01-01T00:00:00", "2026-01-02T01:00:00"),
        ("2026-01-01T23:00:00+00:00", "2026-01-02T07:00:00"),
        ("yesterday", "today"),
        ("1990-01-01T23:00:00", "1990-01-02T07:00:00"),
    ],
)
def test_invalid_sleep_is_rejected(signed_in, start, end):
    body = {"sleep_end": end}
    if start is not None:
        body["sleep_start"] = start

    response = signed_in.post("/api/recovery/sleep", json=body)

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_heatmap_year_and_day_details_date_are_validated(signed_in, user):
    assert signed_in.get(f"/api/recovery/heatmap/{user.id}", query_string={"year": "abc"}).status_code == 400
    assert signed_in.get(f"/api/recovery/heatmap/{user.id}", query_string={"year": "1999"}).status_code == 400
    assert signed_in.get(f"/api/recovery/heatmap/{user.id}", query_string={"year": "2026"}).status_code == 200

    assert signed_in.get(f"/api/recovery/day-details/{user.id}").status_code == 400
    assert signed_in.get(f"/api/recovery/day-details/{user.id}", query_string={"date": "nope"}).status_code == 400
    today = signed_in.get(f"/api/recovery/day-details/{user.id}", query_string={"date": dt.date.today().isoformat()})
    assert today.status_code == 200

    assert signed_in.get(f"/api/recovery/snapshot/{user.id}", query_string={"date": "nope"}).status_code == 400


def test_other_users_day_details_are_hidden(signed_in, user):
    response = signed_in.get(f"/api/recovery/day-details/{user.id + 1000}", query_string={"date": "2026-01-01"})

    assert response.status_code == 404
