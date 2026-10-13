"""Training API routes the other training tests do not reach.

test_training_logging_api, _measurement_api and _model_api cover exercise
search, logging through /sessions/complete and the training model. This
file covers access, the catalogs, plans, the live session routes and the
read-only day, heatmap, analytics and recommendation views.
"""

import datetime as dt
import re

import pytest
from werkzeug.security import generate_password_hash

from backend.app.extensions import db
from backend.app.models.user import User
from backend.app.training.exercises.catalog import load_exercise_catalog
from backend.app.training.models.exercise import Exercise
from backend.app.training.models.training_plan import TrainingPlan


@pytest.fixture
def signed_in(client, user):
    client.post("/auth/login", data={"email": user.email, "password": "password123"})
    return client


@pytest.fixture
def bench_press(app):
    for item in load_exercise_catalog():
        db.session.add(Exercise(**item))
    db.session.commit()
    return Exercise.query.filter_by(slug="bench-press").one()


def test_every_training_route_requires_signing_in(app, client):
    rules = sorted(
        (rule.rule, sorted(rule.methods - {"HEAD", "OPTIONS"}))
        for rule in app.url_map.iter_rules()
        if rule.rule.startswith("/api/training/")
    )
    assert len(rules) == 21

    for rule, methods in rules:
        path = re.sub(r"<(?:int:)?(\w+)>", lambda m: "2026-01-01" if m.group(1) == "date" else "1", rule)
        for method in methods:
            response = getattr(client, method.lower())(path, json={})
            assert response.status_code == 302, (method, path)
            assert "/auth/login" in response.headers["Location"]


def test_catalog_lists(signed_in, bench_press):
    muscles = signed_in.get("/api/training/muscles")
    equipment = signed_in.get("/api/training/equipment")

    assert muscles.status_code == 200 and isinstance(muscles.get_json(), list)
    assert equipment.status_code == 200 and isinstance(equipment.get_json(), list)


def test_plans_can_be_created_activated_edited_and_deleted(signed_in, user):
    first = signed_in.post("/api/training/plans", json={"name": "Push", "is_active": True})
    assert first.status_code == 200
    first = first.get_json()
    assert first["name"] == "Push" and first["is_active"] is True

    second = signed_in.post("/api/training/plans", json={"name": "Pull", "is_active": True}).get_json()
    plans = {p["id"]: p for p in signed_in.get("/api/training/plans").get_json()}
    # Only one plan is active at a time.
    assert plans[first["id"]]["is_active"] is False
    assert plans[second["id"]]["is_active"] is True

    renamed = signed_in.put(f"/api/training/plans/{first['id']}", json={"name": "Push day", "is_active": True})
    assert renamed.status_code == 200
    assert renamed.get_json()["name"] == "Push day"
    plans = {p["id"]: p for p in signed_in.get("/api/training/plans").get_json()}
    assert plans[first["id"]]["is_active"] is True and plans[second["id"]]["is_active"] is False

    deleted = signed_in.delete(f"/api/training/plans/{second['id']}")
    assert deleted.status_code == 200
    assert [p["id"] for p in signed_in.get("/api/training/plans").get_json()] == [first["id"]]


def test_other_users_plans_are_not_reachable(signed_in):
    other = User(username="other", email="other@example.com", password=generate_password_hash("password123"))
    db.session.add(other)
    db.session.flush()
    plan = TrainingPlan(user_id=other.id, name="Theirs")
    db.session.add(plan)
    db.session.commit()

    assert signed_in.put(f"/api/training/plans/{plan.id}", json={"name": "Mine"}).status_code == 404
    assert signed_in.delete(f"/api/training/plans/{plan.id}").status_code == 404
    assert signed_in.get("/api/training/plans").get_json() == []
    db.session.expire_all()
    assert db.session.get(TrainingPlan, plan.id).name == "Theirs"


def test_a_live_session_is_started_once_edited_and_finished(signed_in, bench_press):
    started = signed_in.post("/api/training/sessions/start", json={"fatigue_before": 3})
    assert started.status_code == 200
    session_id = started.get_json()["id"]
    # Starting again while a session is active returns the same one.
    assert signed_in.post("/api/training/sessions/start", json={}).get_json() == {"id": session_id}

    edited = signed_in.post(
        f"/api/training/sessions/{session_id}/exercise/{bench_press.id}",
        json={"sets_done": 3, "reps_done": 8, "load_done": 60},
    )
    assert edited.status_code == 200
    body = edited.get_json()
    assert body["status"] == "ok" and body["exercise_id"] == bench_press.id
    assert (body["sets_done"], body["load_done"]) == (3, 60)

    finished = signed_in.post(f"/api/training/sessions/{session_id}/finish", json={"fatigue_after": 5})
    assert finished.get_json() == {"status": "ok", "id": session_id}
    # A finished session is no longer live.
    assert signed_in.post(f"/api/training/sessions/{session_id}/finish", json={}).status_code == 404


def test_read_only_views_answer_for_a_new_user(signed_in, bench_press):
    for path in (
        "/api/training/today",
        "/api/training/today-session",
        "/api/training/sessions/today",
        "/api/training/heatmap",
        "/api/training/analytics",
        "/api/training/recommendations",
        f"/api/training/day/{dt.date.today().isoformat()}",
    ):
        assert signed_in.get(path).status_code == 200, path



@pytest.mark.parametrize("value", ["not-a-date", "2026-13-01", "2026-02-30", "01-01-2026"])
def test_day_view_rejects_a_bad_date(signed_in, value):
    response = signed_in.get(f"/api/training/day/{value}")

    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid_input"


def test_exercise_list_filters(signed_in, bench_press):
    def slugs(**params):
        body = signed_in.get("/api/training/exercises", query_string=params).get_json()
        return {item["slug"] for item in body["items"]}, body["total"]

    assert "bench-press" in slugs(q="bench")[0]
    assert "bench-press" in slugs(muscle=bench_press.muscles_primary[0])[0]
    assert "bench-press" in slugs(equipment=bench_press.equipment[0])[0]
    assert slugs(q="no-such-exercise-zzz") == (set(), 0)


def test_plan_count_is_capped(signed_in):
    for i in range(50):
        assert signed_in.post("/api/training/plans", json={"name": f"P{i}"}).status_code == 200

    response = signed_in.post("/api/training/plans", json={"name": "One too many"})

    assert response.status_code == 400
    assert response.get_json() == {"error": "too_many_plans"}


def test_today_views_follow_the_active_plan(signed_in, bench_press):
    item = {"exercise": {"id": bench_press.id}, "sets": 3, "reps": 8, "load": 60}
    days = {day: [item] for day in ("mon", "tue", "wed", "thu", "fri", "sat", "sun")}
    plan = signed_in.post("/api/training/plans", json={"name": "Push", "is_active": True, "days": days}).get_json()

    today = signed_in.get("/api/training/today").get_json()
    assert today["plan"] == [{"id": plan["id"], "name": "Push"}]
    assert [e["exercise"]["id"] for e in today["exercises"]] == [bench_press.id]

    session = signed_in.get("/api/training/today-session").get_json()
    assert [e["exercise"]["id"] for e in session["exercises"]] == [bench_press.id]

