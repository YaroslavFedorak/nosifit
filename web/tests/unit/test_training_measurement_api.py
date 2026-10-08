import datetime as dt
from types import SimpleNamespace

import pytest

from backend.app.extensions import db
from backend.app.models.training_session import SessionExercise, TrainingSession
from backend.app.training.exercises.catalog import load_exercise_catalog
from backend.app.training.exercises.prescription import format_entry
from backend.app.training.models.exercise import Exercise
from backend.app.training.plans.plan_generator import PlanGenerator
from backend.app.training.training_analysis.recommendations_engine import (
    build_recommendations,
)


def login(client, email="test@example.com", password="password123"):
    return client.post("/auth/login", data={"email": email, "password": password})


@pytest.fixture
def catalog(app):
    rows = {}

    for item in load_exercise_catalog():
        exercise = Exercise(**item)
        db.session.add(exercise)
        rows[item["slug"]] = exercise

    db.session.commit()
    return rows


def _complete(client, items):
    response = client.post("/api/training/sessions/complete", json={"exercises": items})
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def _item(exercise, **values):
    return {"exercise": {"id": exercise.id}, **values}


def test_exercise_list_exposes_whole_catalog_with_measurements(client, user, catalog):
    login(client)

    items = []
    page = 1
    while True:
        data = client.get(f"/api/training/exercises?page={page}&per_page=100").get_json()
        items.extend(data["items"])
        if len(data["items"]) < 100:
            break
        page += 1
    by_slug = {item["slug"]: item for item in items}

    assert data["total"] == len(catalog)
    assert len(by_slug) == len(catalog)
    assert by_slug["plank"]["measurement_type"] == "duration"
    assert by_slug["plank"]["prescription"]["seconds_max"] > 0
    assert by_slug["push-ups"]["measurement_type"] == "reps"
    assert by_slug["push-ups"]["prescription"]["reps_max"] > 0


def test_mixed_workout_is_stored_and_loaded(client, user, catalog):
    user.weight = 80
    db.session.commit()
    login(client)

    result = _complete(
        client,
        [
            _item(catalog["push-ups"], sets=3, reps=12, load=0),
            _item(catalog["plank"], sets=3, duration_sec=45, load=0),
            _item(catalog["barbell-back-squat"], sets=3, reps=10, load=60),
            _item(catalog["dead-hang"], sets=2, duration_sec=30, load=0),
        ],
    )

    rows = {
        row.exercise_id: row
        for row in SessionExercise.query.filter_by(session_id=result["id"])
    }

    push_up = rows[catalog["push-ups"].id]
    plank = rows[catalog["plank"].id]
    squat = rows[catalog["barbell-back-squat"].id]
    hang = rows[catalog["dead-hang"].id]

    assert (push_up.sets_done, push_up.reps_done, push_up.duration_sec_done) == (
        3,
        "12",
        None,
    )
    assert (plank.sets_done, plank.reps_done, plank.duration_sec_done) == (3, None, 45)
    assert (squat.reps_done, squat.load_done) == ("10", 60)
    assert (hang.sets_done, hang.reps_done, hang.duration_sec_done) == (2, None, 30)
    assert result["internal_load"] > 0

    day = dt.date.today().strftime("%Y-%m-%d")
    details = client.get(f"/api/training/day/{day}").get_json()
    exercises = {item["slug"]: item for item in details["sessions"][0]["exercises"]}

    assert exercises["plank"]["measurement_type"] == "duration"
    assert exercises["plank"]["duration_sec"] == 45
    assert exercises["plank"]["reps"] is None
    assert exercises["push-ups"]["reps"] == "12"
    assert exercises["push-ups"]["duration_sec"] is None


def test_duration_exercises_contribute_to_session_load(client, user, catalog):
    user.weight = 80
    db.session.commit()
    login(client)

    short = _complete(client, [_item(catalog["plank"], sets=3, duration_sec=20)])
    long = _complete(client, [_item(catalog["plank"], sets=3, duration_sec=90)])

    assert 0 < short["internal_load"] < long["internal_load"]


def test_reps_sent_for_duration_exercise_are_not_converted(client, user, catalog):
    login(client)

    result = _complete(client, [_item(catalog["wall-sit"], sets=3, reps="60")])

    row = SessionExercise.query.filter_by(session_id=result["id"]).one()

    assert row.duration_sec_done is None
    assert row.reps_done is None


def test_per_side_reaches_api_responses(client, user, catalog):
    login(client)

    _complete(
        client,
        [
            _item(catalog["bulgarian-split-squat"], sets=3, reps=10),
            _item(catalog["side-plank"], sets=3, duration_sec=30),
            _item(catalog["push-ups"], sets=3, reps=10),
        ],
    )

    day = dt.date.today().strftime("%Y-%m-%d")
    details = client.get(f"/api/training/day/{day}").get_json()
    per_side = {
        item["slug"]: item["per_side"] for item in details["sessions"][0]["exercises"]
    }

    assert per_side == {
        "bulgarian-split-squat": True,
        "side-plank": True,
        "push-ups": False,
    }

    plan = client.post(
        "/api/training/plans",
        json={
            "name": "Sides",
            "days": {"mon": [_item(catalog["side-plank"], sets=3, duration_sec=30)]},
        },
    ).get_json()

    entry = plan["days"]["mon"]["exercises"][0]

    assert entry["per_side"] is True
    assert format_entry(entry) == "3 × 30 sec / side"


def test_plans_store_measurement_specific_fields(client, user, catalog):
    login(client)

    response = client.post(
        "/api/training/plans",
        json={
            "name": "Mixed",
            "is_active": True,
            "days": {
                "mon": [
                    _item(catalog["push-ups"], sets=3, reps="12"),
                    _item(catalog["plank"], sets=3, duration_sec=45),
                    _item(catalog["side-plank"], sets=2, reps="8-12"),
                ]
            },
        },
    )
    assert response.status_code == 200

    exercises = response.get_json()["days"]["mon"]["exercises"]

    assert [format_entry(item) for item in exercises] == [
        "3 × 12",
        "3 × 45 sec",
        "2 × 40 sec / side",
    ]
    assert exercises[1]["reps"] is None
    assert exercises[0]["duration_sec"] is None

    today = client.get("/api/training/today-session").get_json()["exercises"]

    assert {item["exercise"]["slug"]: item["measurement_type"] for item in today} == {
        "push-ups": "reps",
        "plank": "duration",
        "side-plank": "duration",
    }


def test_plan_generator_builds_mixed_workouts(user, catalog):
    profile = SimpleNamespace(workouts_per_week=3, environment="gym", user_id=user.id)

    plan = PlanGenerator(profile).generate()

    entries = {
        item["exercise"]["slug"]: item
        for day in plan.days.values()
        for item in day["exercises"]
    }

    assert entries["plank"]["measurement_type"] == "duration"
    assert entries["plank"]["reps"] is None
    assert entries["plank"]["duration_sec"] > 0
    assert entries["barbell-back-squat"]["measurement_type"] == "reps"
    assert entries["barbell-back-squat"]["reps"] == "4-10"
    assert entries["barbell-back-squat"]["duration_sec"] is None


def test_recommendations_carry_prescriptions(app, user, catalog):
    user.weight = 80
    user.experience = "intermediate"
    user.weak_points = ["core"]
    db.session.commit()

    session = TrainingSession(
        user_id=user.id,
        status="finished",
        started_at=dt.datetime.utcnow() - dt.timedelta(days=1),
        internal_load=50,
    )
    db.session.add(session)
    db.session.flush()

    for slug, values in (
        ("push-ups", {"sets_done": 3, "reps_done": "12"}),
        ("plank", {"sets_done": 3, "duration_sec_done": 45}),
        ("barbell-back-squat", {"sets_done": 3, "reps_done": "10", "load_done": 60}),
        ("dead-hang", {"sets_done": 2, "duration_sec_done": 30}),
    ):
        db.session.add(
            SessionExercise(
                session_id=session.id, exercise_id=catalog[slug].id, **values
            )
        )
    db.session.commit()

    result = build_recommendations(
        user=user,
        sessions=[session],
        target_day=dt.date.today(),
    )

    recommended = result["recommended_exercises"]

    assert recommended
    assert result["patterns"]["pattern_sets"]

    for item in recommended:
        exercise = catalog[item["slug"]]
        assert exercise.movement_pattern != "mobility"
        assert item["measurement_type"] == exercise.measurement_type
        assert item["per_side"] == bool(exercise.prescription.get("per_side"))
        if item["measurement_type"] == "duration":
            assert item["reps"] is None and item["duration_sec"] > 0
        else:
            assert item["duration_sec"] is None and item["reps"]
