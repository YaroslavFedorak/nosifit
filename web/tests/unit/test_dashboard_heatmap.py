"""The dashboard heatmap loads the year in a few queries and still builds
every day exactly as the single-day view does."""

import datetime as dt

import pytest
from sqlalchemy import event

from backend.app.extensions import db
from backend.app.models.nutrition.meal import Meal
from backend.app.models.nutrition.meal_item import MealItem
from backend.app.models.recovery.daily_recovery_snapshot import DailyRecoverySnapshot
from backend.app.models.training_session import SessionExercise, TrainingSession
from backend.app.services.dashboard import aggregator
from backend.app.training.exercises.catalog import load_exercise_catalog
from backend.app.training.models.exercise import Exercise

TODAY = dt.date.today()


def days_ago(n):
    return TODAY - dt.timedelta(days=n)


def at(day, hour):
    return dt.datetime.combine(day, dt.time(hour))


@pytest.fixture
def exercises(app):
    for item in load_exercise_catalog()[:4]:
        db.session.add(Exercise(**item))
    db.session.commit()
    return Exercise.query.order_by(Exercise.id).all()


def add_session(user, day, hour, exercises, status="finished", load=120):
    session = TrainingSession(
        user_id=user.id,
        started_at=at(day, hour),
        finished_at=at(day, hour + 1),
        status=status,
        internal_load=load,
    )
    db.session.add(session)
    db.session.flush()
    for exercise in exercises:
        db.session.add(SessionExercise(session_id=session.id, exercise_id=exercise.id))


def add_meal(user, day, time, items):
    meal = Meal(user_id=user.id, date=day, time=time, name="Meal", category="lunch",
                total_calories=sum(i[1] for i in items))
    db.session.add(meal)
    db.session.flush()
    for name, kcal, fiber in items:
        db.session.add(MealItem(meal_id=meal.id, name=name, calories=kcal, protein=1, fat=1, carbs=1, fiber=fiber))


def add_snapshot(user, day, score, sleep_minutes=None):
    db.session.add(DailyRecoverySnapshot(
        user_id=user.id, date=day, sleep_score=60, sleep_duration_minutes=sleep_minutes,
        habit_score=50, training_score=50, energy_score=50, recovery_score=score,
    ))


@pytest.fixture
def a_year_of_data(user, exercises):
    # Two finished sessions on one day: the later one counts. The active
    # one is ignored.
    add_session(user, days_ago(1), 8, exercises[:1])
    add_session(user, days_ago(1), 18, exercises[:3])
    add_session(user, days_ago(1), 20, exercises, status="active")
    add_meal(user, days_ago(3), dt.time(12), [("рис", 300, 2.0), ("печиво", 200, 0.5)])
    add_meal(user, days_ago(3), None, [("яйця", 150, 0.0)])
    add_snapshot(user, days_ago(3), 70, sleep_minutes=450)
    add_snapshot(user, days_ago(200), 40)
    add_session(user, days_ago(364), 10, exercises[:2], load=400)
    # Outside the 365-day window.
    add_meal(user, days_ago(365), dt.time(9), [("рис", 500, 1.0)])
    add_snapshot(user, days_ago(365), 90)
    db.session.commit()


def count_queries(func):
    statements = []

    def before(conn, cursor, statement, *args):
        statements.append(statement)

    event.listen(db.engine, "before_cursor_execute", before)
    try:
        result = func()
    finally:
        event.remove(db.engine, "before_cursor_execute", before)
    return result, len(statements)


def test_every_day_matches_the_single_day_view(user, a_year_of_data):
    heatmap = aggregator.get_heatmap(user.id)

    dates = [day["date"] for day in heatmap["days"]]
    assert dates == [d.isoformat() for d in (days_ago(364), days_ago(200), days_ago(3), days_ago(1))]
    db.session.expire_all()
    for day in heatmap["days"]:
        expected = aggregator._build_day(user.id, dt.date.fromisoformat(day["date"]))
        assert {k: v for k, v in day.items() if k != "level"} == expected

    by_date = {day["date"]: day for day in heatmap["days"]}
    assert by_date[days_ago(1).isoformat()]["training"]["exercise_count"] == 3
    assert by_date[days_ago(3).isoformat()]["nutrition"]["calories"] == 650
    assert by_date[days_ago(3).isoformat()]["recovery"]["sleep_hours"] == 7.5
    assert heatmap["start_date"] == days_ago(364).isoformat()
    assert heatmap["end_date"] == TODAY.isoformat()


def test_the_year_is_loaded_in_a_handful_of_queries(user, a_year_of_data):
    user_id = user.id
    db.session.expire_all()

    _, queries = count_queries(lambda: aggregator.get_heatmap(user_id))

    # Sessions, their exercises, meals, their items, recovery snapshots.
    assert queries <= 5


def test_the_api_serves_the_same_heatmap(client, user, a_year_of_data):
    client.post("/auth/login", data={"email": user.email, "password": "password123"})

    response = client.get("/api/dashboard/heatmap")

    assert response.status_code == 200
    db.session.expire_all()
    assert response.get_json() == aggregator.get_heatmap(user.id)
