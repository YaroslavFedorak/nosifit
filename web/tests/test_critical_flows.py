"""End-to-end checks of what users do every day, through the HTTP API.

Each test follows one scenario from the request to what the dashboard shows
afterwards, so a refactor that keeps every unit test green but breaks the
way the pieces fit together still fails here. Assertions cover status
codes, access control and the fields the web client and the Telegram bot
read, not every field of every response.
"""

import datetime as dt

import pytest

from backend.app.extensions import db
from backend.app.models.recovery.habit import RecoveryHabit
from backend.app.training.exercises.catalog import load_exercise_catalog
from backend.app.training.models.exercise import Exercise

PASSWORD = "password123"

APP_PAGES = [
    "/dashboard/",
    "/training/",
    "/nutrition/",
    "/recovery/",
    "/profile/",
    "/tracker/",
    "/training_plan/",
    "/equipment/",
    "/premium",
    "/assessment/",
    "/questionnaire/",
]

PUBLIC_PAGES = ["/", "/about", "/pricing", "/contact", "/demo", "/info", "/auth/login", "/auth/register"]


@pytest.fixture
def signed_in(client, user):
    response = client.post("/auth/login", data={"email": user.email, "password": PASSWORD})
    assert response.status_code == 302
    return client


@pytest.fixture
def bench_press(app):
    for item in load_exercise_catalog():
        db.session.add(Exercise(**item))
    db.session.commit()
    return Exercise.query.filter_by(slug="bench-press").one()


def get_json(client, path):
    response = client.get(path)
    assert response.status_code == 200, (path, response.get_json(silent=True))
    return response.get_json()


def dashboard_today(client):
    return get_json(client, "/api/dashboard/today")


# --- Pages ----------------------------------------------------------------------------


@pytest.mark.parametrize("path", PUBLIC_PAGES)
def test_public_pages_render(client, path):
    assert client.get(path).status_code == 200


@pytest.mark.parametrize("path", APP_PAGES)
def test_app_pages_render_for_a_signed_in_user(signed_in, path):
    assert signed_in.get(path).status_code == 200


@pytest.mark.parametrize("path", APP_PAGES)
def test_app_pages_send_guests_to_login(client, path):
    response = client.get(path)
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


# --- Dashboard ------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "/api/dashboard/today",
        "/api/dashboard/heatmap",
        "/api/dashboard/recommendation",
        "/api/dashboard/training",
    ],
)
def test_dashboard_api_is_private(client, path):
    response = client.get(path)
    assert response.status_code in (302, 401)
    assert response.get_json(silent=True) is None or "error" in response.get_json()


def test_dashboard_of_an_empty_day(signed_in):
    today = dashboard_today(signed_in)

    assert today["date"] == dt.date.today().isoformat()
    assert today["daily_score"] == 0
    assert today["training"]["completed"] is False
    assert today["nutrition"]["calories"] == 0
    assert today["recovery"]["sleep_hours"] == 0

    assert set(get_json(signed_in, "/api/dashboard/heatmap")) >= {"days", "start_date", "end_date"}
    assert set(get_json(signed_in, "/api/dashboard/recommendation")) >= {"daily", "categories"}
    day = get_json(signed_in, f"/api/dashboard/day/{dt.date.today().isoformat()}")
    assert day["date"] == today["date"]


def test_dashboard_day_rejects_a_bad_date(signed_in):
    response = signed_in.get("/api/dashboard/day/not-a-date")
    assert response.status_code == 404
    assert response.get_json() == {"error": "invalid_date_or_no_data"}


# --- Training -------------------------------------------------------------------------


def test_workout_from_start_to_finish_reaches_the_dashboard(signed_in, bench_press):
    started = signed_in.post("/api/dashboard/training/session", json={"fatigue_before": 3})
    assert started.status_code == 201
    session = started.get_json()["session"]
    assert session["status"] == "active"
    assert session["fatigue_before"] == 3

    added = signed_in.post(
        f"/api/dashboard/training/session/{session['id']}/exercise",
        json={"exercise_id": bench_press.id},
    )
    assert added.status_code == 201
    assert added.get_json()["exercise"]["exercise_id"] == bench_press.id

    edited = signed_in.patch(
        f"/api/dashboard/training/session/{session['id']}/exercise/{bench_press.id}",
        json={"sets_done": 3, "reps_done": 8, "load_done": 60, "rpe": 8},
    )
    assert edited.status_code == 200
    exercise = edited.get_json()["exercise"]
    assert (exercise["sets"], exercise["reps"], exercise["load"], exercise["rpe"]) == (3, "8", 60.0, 8.0)

    finished = signed_in.post(
        f"/api/dashboard/training/session/{session['id']}/finish",
        json={"fatigue_after": 6},
    )
    assert finished.status_code == 200
    session = finished.get_json()["session"]
    assert session["status"] != "active"
    assert session["exercise_count"] == 1
    assert session["fatigue_after"] == 6

    training = dashboard_today(signed_in)["training"]
    assert training["completed"] is True
    assert training["exercise_count"] == 1


def test_workout_edits_validate_input(signed_in, bench_press):
    session = signed_in.post("/api/dashboard/training/session", json={}).get_json()["session"]
    signed_in.post(
        f"/api/dashboard/training/session/{session['id']}/exercise",
        json={"exercise_id": bench_press.id},
    )

    bad_sets = signed_in.patch(
        f"/api/dashboard/training/session/{session['id']}/exercise/{bench_press.id}",
        json={"sets_done": 1000},
    )
    assert bad_sets.status_code == 400
    assert bad_sets.get_json() == {"error": "invalid_exercise_data"}

    bad_fatigue = signed_in.post(
        f"/api/dashboard/training/session/{session['id']}/finish", json={"fatigue_after": 99}
    )
    assert bad_fatigue.status_code == 400
    assert bad_fatigue.get_json() == {"error": "invalid_fatigue"}


def test_workouts_of_other_users_are_not_reachable(signed_in, bench_press, app):
    from backend.app.models.training_session import TrainingSession
    from backend.app.models.user import User

    other = User(username="other", email="other@example.com", password="x")
    db.session.add(other)
    db.session.flush()
    foreign = TrainingSession(user_id=other.id, status="active")
    db.session.add(foreign)
    db.session.commit()

    assert signed_in.get(f"/api/dashboard/training/session/{foreign.id}").status_code == 404
    response = signed_in.post(
        f"/api/dashboard/training/session/{foreign.id}/exercise",
        json={"exercise_id": bench_press.id},
    )
    assert response.status_code == 404
    assert signed_in.post(f"/api/dashboard/training/session/{foreign.id}/finish", json={}).status_code == 404


# --- Nutrition, water, weight ---------------------------------------------------------


def test_logged_food_water_and_weight_reach_the_dashboard(signed_in):
    meal = signed_in.post("/api/nutrition/meals", json={"category": "lunch"})
    assert meal.status_code == 201
    meal_id = meal.get_json()["id"]

    item = signed_in.post(
        "/api/nutrition/items",
        json={"meal_id": meal_id, "name": "Rice", "calories": 130, "protein": 2.7, "fat": 0.3, "carbs": 28},
    )
    assert item.status_code == 201
    item_id = item.get_json()["id"]

    day = get_json(signed_in, "/api/nutrition/day")
    assert day["kcal"] == pytest.approx(130, abs=1)
    assert [m["id"] for m in day["meals"]] == [meal_id]

    water = signed_in.post("/api/nutrition/water", json={"amount": 0.5})
    assert water.status_code == 200
    assert get_json(signed_in, "/api/nutrition/water")["amount"] == pytest.approx(0.5)
    # The dashboard's water widget reads the nutrition day.
    assert get_json(signed_in, "/api/nutrition/day")["water"] == pytest.approx(0.5)

    weight = signed_in.post("/api/nutrition/weight", json={"weight": 80.5})
    assert weight.status_code == 200
    assert get_json(signed_in, "/api/nutrition/weight")["weight"] == pytest.approx(80.5)

    assert dashboard_today(signed_in)["nutrition"]["calories"] == pytest.approx(130, abs=1)

    assert signed_in.delete(f"/api/nutrition/items/{item_id}").status_code == 200
    assert get_json(signed_in, "/api/nutrition/day")["kcal"] == 0


def test_nutrition_summaries_answer_for_a_new_user(signed_in):
    assert set(get_json(signed_in, "/api/nutrition/stats")) >= {"kcal", "weight", "avg_kcal"}
    assert set(get_json(signed_in, "/api/nutrition/recommendations")) >= {"recommendations", "summary"}

    nothing = signed_in.post("/api/nutrition/copy-yesterday", json={})
    assert nothing.status_code == 400
    assert nothing.get_json()["code"] == "nothing_to_copy"


def test_nutrition_input_is_validated(signed_in):
    assert signed_in.post("/api/nutrition/water", json={"amount": 50}).status_code == 400
    assert signed_in.post("/api/nutrition/weight", json={"weight": 5}).status_code == 400
    assert signed_in.post("/api/nutrition/items", json={"name": "Rice"}).status_code == 400


# --- Recovery -------------------------------------------------------------------------


def test_sleep_and_habits_reach_the_recovery_snapshot_and_dashboard(signed_in, user):
    habit = RecoveryHabit(slug="walk", name="Walk", points=5)
    db.session.add(habit)
    db.session.commit()

    catalog = get_json(signed_in, "/api/recovery/habits/list")
    assert [h["slug"] for h in catalog] == ["walk"]

    added = signed_in.post(f"/api/recovery/habits/add/{habit.id}")
    assert added.status_code == 200
    user_habit_id = added.get_json()["user_habit_id"]

    logged = signed_in.post("/api/recovery/habits/logs", json={"user_habit_id": user_habit_id})
    assert logged.status_code == 200
    habits = get_json(signed_in, f"/api/recovery/habits/user/{user.id}")
    assert [(h["slug"], h["completed"]) for h in habits] == [("walk", True)]

    today = dt.date.today()
    yesterday = today - dt.timedelta(days=1)
    sleep = signed_in.post(
        "/api/recovery/sleep",
        json={"sleep_start": f"{yesterday.isoformat()}T23:00:00", "sleep_end": f"{today.isoformat()}T06:30:00"},
    )
    assert sleep.status_code == 201
    assert sleep.get_json()["duration_minutes"] == 450

    snapshot = get_json(signed_in, f"/api/recovery/snapshot/{user.id}")
    assert snapshot["sleep_duration_minutes"] == 450
    assert set(get_json(signed_in, f"/api/recovery/heatmap/{user.id}")) >= {"days"}
    assert set(get_json(signed_in, f"/api/recovery/recommendations/{user.id}")) >= {"recommendations"}

    assert dashboard_today(signed_in)["recovery"]["sleep_hours"] == pytest.approx(7.5)


def test_recovery_data_of_other_users_is_hidden(signed_in, user):
    other_id = user.id + 1000
    for path in (
        f"/api/recovery/snapshot/{other_id}",
        f"/api/recovery/habits/user/{other_id}",
        f"/api/recovery/heatmap/{other_id}",
        f"/api/recovery/recommendations/{other_id}",
    ):
        assert signed_in.get(path).status_code == 404, path
