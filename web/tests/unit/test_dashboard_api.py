"""Dashboard API: the parts test_critical_flows does not already cover."""

import pytest

from backend.app.extensions import db
from backend.app.training.exercises.catalog import load_exercise_catalog
from backend.app.training.models.exercise import Exercise

GUARDED = [
    ("get", "/api/dashboard/today"),
    ("get", "/api/dashboard/heatmap"),
    ("get", "/api/dashboard/recommendation"),
    ("get", "/api/dashboard/day/2026-01-01"),
    ("get", "/api/dashboard/training"),
    ("get", "/api/dashboard/training/exercises"),
    ("post", "/api/dashboard/training/session"),
    ("get", "/api/dashboard/training/session/1"),
    ("post", "/api/dashboard/training/session/1/exercise"),
    ("patch", "/api/dashboard/training/session/1/exercise/x"),
    ("post", "/api/dashboard/training/session/1/finish"),
]


@pytest.fixture
def catalog(app):
    for item in load_exercise_catalog():
        db.session.add(Exercise(**item))
    db.session.commit()
    return {e.slug: e for e in Exercise.query.all()}


@pytest.fixture
def signed_in(client, user):
    client.post("/auth/login", data={"email": user.email, "password": "password123"})
    return client


@pytest.mark.parametrize("method, path", GUARDED)
def test_every_dashboard_route_requires_signing_in(client, method, path):
    response = getattr(client, method)(path, json={})

    assert response.status_code == 401
    assert response.get_json()["code"] == "authentication_required"


def test_training_summary_and_session_follow_a_workout(signed_in, catalog):
    empty = signed_in.get("/api/dashboard/training")
    assert empty.status_code == 200
    assert set(empty.get_json()) == {"session", "summary"}

    session = signed_in.post("/api/dashboard/training/session", json={"fatigue_before": 4}).get_json()["session"]
    signed_in.post(
        f"/api/dashboard/training/session/{session['id']}/exercise", json={"exercise_id": catalog["bench-press"].id}
    )

    fetched = signed_in.get(f"/api/dashboard/training/session/{session['id']}")
    assert fetched.status_code == 200
    body = fetched.get_json()
    assert set(body) == {"session", "summary"}
    assert body["session"]["id"] == session["id"]
    assert body["session"]["status"] == "active"
    assert [e["exercise_id"] for e in body["session"]["exercises"]] == [catalog["bench-press"].id]

    today = signed_in.get("/api/dashboard/training").get_json()
    assert today["session"]["id"] == session["id"]


def test_exercise_search_filters_the_catalog(signed_in, catalog):
    # Without a search the list stops at 100 exercises (existing behaviour).
    everything = signed_in.get("/api/dashboard/training/exercises").get_json()["exercises"]
    assert len(everything) == min(100, len(catalog))

    found = signed_in.get("/api/dashboard/training/exercises", query_string={"search": "bench"}).get_json()
    slugs = {item["slug"] for item in found["exercises"]}
    assert "bench-press" in slugs
    assert all("bench" in slug for slug in slugs)


@pytest.mark.parametrize("value", [None, "", True, 0, [], {}])
def test_adding_an_exercise_needs_an_exercise_id(signed_in, catalog, value):
    session = signed_in.post("/api/dashboard/training/session", json={}).get_json()["session"]

    response = signed_in.post(f"/api/dashboard/training/session/{session['id']}/exercise", json={"exercise_id": value})

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "exercise_id_required",
        "code": "exercise_id_required",
        "message": "Exercise id required",
    }


def test_adding_an_unknown_exercise_or_to_an_unknown_session_is_not_found(signed_in, catalog):
    session = signed_in.post("/api/dashboard/training/session", json={}).get_json()["session"]

    unknown_exercise = signed_in.post(
        f"/api/dashboard/training/session/{session['id']}/exercise", json={"exercise_id": "no-such-exercise"}
    )
    unknown_session = signed_in.post(
        "/api/dashboard/training/session/999999/exercise", json={"exercise_id": catalog["bench-press"].id}
    )

    for response in (unknown_exercise, unknown_session):
        assert response.status_code == 404
        assert response.get_json() == {
            "error": "session_or_exercise_not_found",
            "code": "session_or_exercise_not_found",
            "message": "Session or exercise not found",
        }


def test_starting_a_session_validates_fatigue(signed_in):
    response = signed_in.post("/api/dashboard/training/session", json={"fatigue_before": 99})

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "invalid_fatigue",
        "code": "invalid_fatigue",
        "message": "Invalid fatigue",
    }
