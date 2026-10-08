"""Integration of the v2 training model with the API, database and recovery."""

import datetime as dt

import pytest
from sqlalchemy import event

from backend.app.extensions import db
from backend.app.models.training_session import SessionExercise, TrainingSession
from backend.app.models.user_equipment import UserEquipment
from backend.app.models.user_goals import UserTrainingGoals
from backend.app.models.user_profile import UserProfile
from backend.app.services.training.model import TrainingModelService
from backend.app.services.training.model import parameters as P
from backend.app.services.training.model.repository import load_context
from backend.app.training.exercises.catalog import load_exercise_catalog
from backend.app.training.models.equipment import TEEquipment
from backend.app.training.models.exercise import Exercise
from backend.app.training.training_analysis.recommendations_engine import build_recommendations

MUSCLES = {
    "chest", "lats", "upper-back", "traps", "shoulders", "biceps", "triceps", "forearms",
    "abs", "obliques", "core", "lower-back", "quads", "hamstrings", "glutes", "adductors",
    "calves", "hip-flexors", "neck",
}

LEGACY_KEYS = {
    "load", "muscles", "patterns", "progression", "recovery", "diversity",
    "frequency", "recommended_exercises", "summary",
}


def login(client):
    return client.post("/auth/login", data={"email": "test@example.com", "password": "password123"})


@pytest.fixture
def catalog(app):
    rows = {}
    for item in load_exercise_catalog():
        exercise = Exercise(**item)
        db.session.add(exercise)
        rows[item["slug"]] = exercise
    db.session.commit()
    return rows


def add_session(user, catalog, days_ago, items, status="finished"):
    finished = dt.datetime.utcnow() - dt.timedelta(days=days_ago, minutes=5)
    session = TrainingSession(
        user_id=user.id, status=status, started_at=finished - dt.timedelta(hours=1), finished_at=finished
    )
    db.session.add(session)
    db.session.flush()
    for slug, values in items:
        db.session.add(SessionExercise(session_id=session.id, exercise_id=catalog[slug].id, **values))
    db.session.commit()
    return session


def count_queries(app, func):
    statements = []

    def before(conn, cursor, statement, *args):
        statements.append(statement)

    engine = db.engine
    event.listen(engine, "before_cursor_execute", before)
    try:
        func()
    finally:
        event.remove(engine, "before_cursor_execute", before)
    return len(statements)


# --- session finish / complete --------------------------------------------


def test_completed_session_reports_muscle_sets_not_exercise_ids(client, user, catalog):
    login(client)
    response = client.post(
        "/api/training/sessions/complete",
        json={
            "exercises": [
                {"exercise": {"id": catalog["bench-press"].id}, "sets": 4, "reps": "8", "load": 60, "rpe": 8},
                {"exercise": {"id": catalog["plank"].id}, "sets": 3, "duration_sec": 45},
            ]
        },
    )
    assert response.status_code == 200, response.get_json()
    data = response.get_json()
    assert "muscle_loads" not in data
    assert set(data["muscle_sets"]) <= MUSCLES
    assert data["muscle_sets"]["chest"] > data["muscle_sets"]["triceps"] > 0
    assert data["hard_sets"] > 0 and data["session_training_stress_proxy"] >= data["hard_sets"]
    assert data["volume_load_kg"] == pytest.approx(4 * 8 * 60)

    stored = db.session.get(TrainingSession, data["id"])
    assert set(stored.muscle_loads) <= MUSCLES  # regression: used to hold exercise ids


# --- recommendations ---------------------------------------------------------


def test_recommendations_endpoint_keeps_contract_and_adds_muscle_status(client, user, catalog):
    add_session(user, catalog, 2, [("bench-press", {"sets_done": 4, "reps_done": "8", "rpe": 8})])
    login(client)
    data = client.get("/api/training/recommendations").get_json()

    assert LEGACY_KEYS <= set(data)
    assert data["model_version"] == P.MODEL_VERSION
    assert {"weak", "balanced", "overloaded", "totals", "balance_ratio"} <= set(data["muscles"])
    assert data["recommended_exercises"]
    for item in data["recommended_exercises"]:
        assert {"exercise", "slug", "sets", "reps", "duration_sec", "per_side", "reasons", "target_rir"} <= set(item)
        assert all(reason.startswith("recommendations.training.reasons.") for reason in item["reasons"])

    statuses = {row["muscle"]: row for row in data["muscle_status"]}
    assert statuses["chest"]["readiness"] in ("low", "moderate", "ready", "recovered")
    assert statuses["chest"]["target"] is not None
    assert set(statuses) <= MUSCLES


def test_recommendation_queries_do_not_grow_with_history(app, user, catalog):
    add_session(user, catalog, 1, [("bench-press", {"sets_done": 4, "reps_done": "8"})])
    small = count_queries(app, lambda: build_recommendations(user, target_day=dt.date.today()))

    for days in range(2, 40, 2):
        add_session(
            user,
            catalog,
            days,
            [
                ("bench-press", {"sets_done": 4, "reps_done": "8"}),
                ("barbell-back-squat", {"sets_done": 4, "reps_done": "6"}),
                ("barbell-row", {"sets_done": 3, "reps_done": "10"}),
            ],
        )
    large = count_queries(app, lambda: build_recommendations(user, target_day=dt.date.today()))

    assert large == small
    assert large <= 12


def test_given_sessions_are_analysed(app, user, catalog):
    session = add_session(user, catalog, 1, [("bench-press", {"sets_done": 10, "reps_done": "8", "rpe": 10})])
    result = build_recommendations(user=user, sessions=[session], target_day=dt.date.today())
    statuses = {row["muscle"]: row for row in result["muscle_status"]}
    assert statuses["chest"]["readiness"] in ("low", "moderate")


# --- heatmap ----------------------------------------------------------------


def test_heatmap_reports_intensity_percent_and_hard_sets(client, user, catalog):
    add_session(user, catalog, 0, [("bench-press", {"sets_done": 5, "reps_done": "8", "rpe": 9})])
    login(client)
    days = client.get("/api/training/heatmap").get_json()["days"]
    assert all({"date", "hard_sets", "intensity_percent", "is_today"} <= set(day) for day in days)
    assert all({"percent", "load", "level"}.isdisjoint(day) for day in days)
    trained = [day for day in days if day["hard_sets"] > 0]
    assert trained and all(1 <= day["intensity_percent"] <= 100 for day in trained)
    assert all(day["intensity_percent"] == 0 for day in days if day["hard_sets"] == 0)


def test_heatmap_queries_are_constant(app, client, user, catalog):
    login(client)
    for days in range(1, 30, 3):
        add_session(user, catalog, days, [("bench-press", {"sets_done": 4, "reps_done": "8"})])
    queries = count_queries(app, lambda: client.get("/api/training/heatmap"))
    assert queries <= 10


# --- context -----------------------------------------------------------------


def test_context_reads_profile_goals_and_equipment(app, user):
    db.session.add(
        UserProfile(user_id=user.id, training_location="home", goal="muscle_gain", experience="advanced",
                    workouts_per_week=4, weight=82)
    )
    db.session.add(UserTrainingGoals(user_id=user.id, primary_goal="strength", focus_upper=9, focus_lower=5, focus_core=2))
    dumbbells = TEEquipment(slug="dumbbells", name="Dumbbells")
    db.session.add(dumbbells)
    db.session.flush()
    db.session.add(UserEquipment(user_id=user.id, equipment_id=dumbbells.id, available=True))
    user.weak_points = ["back"]
    db.session.commit()

    context = load_context(user)
    assert context.goal == "strength"  # onboarding training goal wins
    assert context.experience == "advanced"  # from the profile, not the User default
    assert context.workouts_per_week == 4
    assert context.available_equipment == frozenset({"dumbbells", "bodyweight"})
    assert {"lats", "upper-back"} <= context.weak_muscles
    assert context.focus["chest"] == 9 and context.focus["abs"] == 2
    assert context.body_weight_kg == 82


@pytest.mark.parametrize(
    "raw, goal",
    [("lose", "fat_loss"), ("maintain", "maintenance"), ("gain", "hypertrophy"),
     ("recomposition", "hypertrophy"), ("performance", "general_fitness"), (None, "general_fitness")],
)
def test_goal_vocabulary_is_normalised(app, user, raw, goal):
    db.session.add(UserProfile(user_id=user.id, training_location="gym", goal=raw))
    db.session.commit()
    assert load_context(user).goal == goal


# --- questionnaire -----------------------------------------------------------


def test_questionnaire_saves_weak_points(client, user):
    login(client)
    response = client.post(
        "/questionnaire/",
        data={"environment": "home", "weak_points": ["back", "core", "nonsense"], "strong_points": ["legs"]},
    )
    assert response.status_code == 302
    db.session.refresh(user)
    assert user.weak_points == ["back", "core"]
    assert user.strong_points == ["legs"]
    assert user.environment == "home"

    page = client.get("/questionnaire/").get_data(as_text=True)
    assert 'name="weak_points" value="back" checked' in page


# --- recovery ----------------------------------------------------------------


def test_recovery_day_details_without_snapshot(client, user, catalog):
    add_session(user, catalog, 0, [("barbell-back-squat", {"sets_done": 5, "reps_done": "5", "rpe": 9})])
    login(client)
    today = dt.date.today().isoformat()
    response = client.get(f"/api/recovery/day-details/{user.id}?date={today}")
    assert response.status_code == 200, response.get_json()
    training = response.get_json()["training"]
    assert "load" not in training
    assert training["readiness_level"] in ("low", "moderate", "ready", "recovered")
    assert training["hard_sets"] > 0


def test_recovery_training_score_is_readiness(app, user, catalog):
    assert TrainingModelService.training_readiness_score(user) == 100
    add_session(user, catalog, 0, [("barbell-back-squat", {"sets_done": 10, "reps_done": "5", "rpe": 10})])
    assert TrainingModelService.training_readiness_score(user) < 100


def test_recovery_recommendations_use_muscle_names(app, user, catalog):
    from backend.app.services.recovery.recommendation_service import RecommendationService

    add_session(user, catalog, 0, [("bench-press", {"sets_done": 20, "reps_done": "8", "rpe": 10})])
    recs = RecommendationService.build_recommendations(user.id)
    muscles = [rec.get("muscle") for rec in recs if rec.get("type") in ("muscle", "exercise")]
    assert muscles and set(muscles) <= MUSCLES
    assert any(rec["id"] == "rest_chest" for rec in recs)


def test_profile_is_the_only_source_when_present(app, user):
    """With a profile, legacy User columns are never read, even if they hold values."""
    user.goal, user.experience, user.weight, user.workouts_per_week = "strength", "advanced", 99, 6
    user.environment = "gym"
    db.session.add(UserProfile(user_id=user.id, training_location="home"))
    db.session.commit()

    context = load_context(user)
    assert context.goal == "general_fitness"
    assert context.experience == "beginner"
    assert context.body_weight_kg is None
    assert context.workouts_per_week == P.DEFAULT_WORKOUTS_PER_WEEK
    assert context.available_equipment == frozenset({"bodyweight"})  # home, nothing configured


def test_user_columns_are_used_only_without_a_profile(app, user):
    user.goal, user.experience, user.weight = "strength", "advanced", 90
    db.session.commit()
    context = load_context(user)
    assert (context.goal, context.experience, context.body_weight_kg) == ("strength", "advanced", 90)


def test_legacy_exercise_id_muscle_loads_are_ignored(client, user, catalog):
    """Sessions stored before v2 hold {exercise_id: number} in muscle_loads."""
    from backend.app.dashboard.training import TrainingDashboardService

    session = add_session(user, catalog, 1, [("bench-press", {"sets_done": 4, "reps_done": "8", "rpe": 8})])
    session.muscle_loads = {catalog["bench-press"].id: 480.0}
    db.session.commit()

    login(client)
    data = client.get("/api/training/recommendations").get_json()
    named = set(data["muscles"]["totals"]) | set(data["muscles"]["weak"]) | set(data["muscles"]["overloaded"])
    named |= {row["muscle"] for row in data["muscle_status"]}
    assert named <= MUSCLES
    assert data["muscles"]["totals"]["chest"] > 0  # computed from the logged sets

    summary = TrainingDashboardService.get_session(user.id, session.id)["summary"]["muscles"]
    assert set(summary["weak"] + summary["balanced"] + summary["overloaded"]) <= MUSCLES


# --- re-saving today's workout ---------------------------------------------


def _save(client, items, session_id=None):
    payload = {"exercises": items}
    if session_id is not None:
        payload["session_id"] = session_id
    response = client.post("/api/training/sessions/complete", json=payload)
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def test_saving_after_each_exercise_keeps_one_session(client, user, catalog):
    """Regression: saving the growing workout after every exercise created a
    new session each time, so earlier exercises were counted again."""
    from backend.app.training.models.performance_state import PerformanceState

    login(client)
    push = {"exercise": {"id": catalog["push-ups"].id}, "sets": 3, "reps": "33"}
    plank = {"exercise": {"id": catalog["plank"].id}, "sets": 2, "duration_sec": 120}
    back = {"exercise": {"id": catalog["back-extension"].id}, "sets": 4, "reps": "7-12", "load": 15}

    first = _save(client, [push])
    second = _save(client, [push, plank], first["id"])
    third = _save(client, [push, plank, back], second["id"])

    assert first["id"] == second["id"] == third["id"]
    sessions = TrainingSession.query.filter_by(user_id=user.id).all()
    assert len(sessions) == 1
    assert sorted(e.exercise_id for e in sessions[0].exercises) == sorted(
        catalog[s].id for s in ("push-ups", "plank", "back-extension")
    )
    assert sessions[0].status == "finished"
    assert third["hard_sets"] > second["hard_sets"] > first["hard_sets"]
    assert set(third["muscle_sets"]) <= MUSCLES

    # One save of the full workout gives the same numbers as saving it in steps.
    one_shot_user_hard_sets = third["hard_sets"]
    performance = PerformanceState.query.filter_by(user_id=user.id).all()
    assert len(performance) == 1
    assert performance[0].training_load == pytest.approx(sessions[0].internal_load)
    assert one_shot_user_hard_sets == pytest.approx(
        TrainingModelService.session_summary(sessions[0])["hard_sets"]
    )


def test_resave_can_remove_an_exercise(client, user, catalog):
    login(client)
    push = {"exercise": {"id": catalog["push-ups"].id}, "sets": 3, "reps": "10"}
    plank = {"exercise": {"id": catalog["plank"].id}, "sets": 2, "duration_sec": 60}
    first = _save(client, [push, plank])
    _save(client, [push], first["id"])
    session = db.session.get(TrainingSession, first["id"])
    assert [e.exercise_id for e in session.exercises] == [catalog["push-ups"].id]


@pytest.mark.parametrize("session_id", ["abc", -1, 0, True, None])
def test_invalid_session_id_creates_a_new_session(client, user, catalog, session_id):
    login(client)
    push = {"exercise": {"id": catalog["push-ups"].id}, "sets": 3, "reps": "10"}
    first = _save(client, [push])
    second = _save(client, [push], session_id)
    assert second["id"] != first["id"]


def test_other_users_or_old_sessions_are_never_resaved(client, user, catalog):
    from backend.app.models.user import User
    from werkzeug.security import generate_password_hash

    other = User(username="other", email="other@example.com", password=generate_password_hash("x" * 12))
    db.session.add(other)
    db.session.commit()
    foreign = add_session(other, catalog, 0, [("plank", {"sets_done": 2, "duration_sec_done": 60})])
    old = add_session(user, catalog, 3, [("plank", {"sets_done": 2, "duration_sec_done": 60})])

    login(client)
    push = {"exercise": {"id": catalog["push-ups"].id}, "sets": 3, "reps": "10"}
    for target in (foreign, old):
        result = _save(client, [push], target.id)
        assert result["id"] != target.id
        db.session.refresh(target)
        assert [e.exercise_id for e in target.exercises] == [catalog["plank"].id]
