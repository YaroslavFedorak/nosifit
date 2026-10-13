"""SQL queries per call for the API endpoints the pages and the bot load
most. The count must stay small and must not grow with the user's history:
growth with history is how an N+1 shows up (the dashboard heatmap ran
~1,100 queries per call before #60).
"""

import datetime as dt

import pytest
from sqlalchemy import event

from backend.app.extensions import db
from backend.app.models.nutrition.meal import Meal
from backend.app.models.nutrition.meal_item import MealItem
from backend.app.models.training_session import SessionExercise, TrainingSession
from backend.app.training.exercises.catalog import load_exercise_catalog
from backend.app.training.models.exercise import Exercise

TODAY = dt.date.today()

BUDGETS = {
    "/api/dashboard/today": 15,
    "/api/dashboard/heatmap": 6,
    "/api/dashboard/recommendation": 40,
    "/api/dashboard/training": 10,
    "/api/nutrition/day": 15,
    "/api/nutrition/stats": 6,
    "/api/nutrition/heatmap": 4,
    "/api/training/today": 6,
    "/api/training/heatmap": 6,
    "/api/training/analytics": 10,
    "/api/training/recommendations": 12,
    "/api/training/sessions/today": 6,
    "/api/training/exercises/recent": 6,
    "/api/recovery/snapshot/{user}?date={today}": 20,
    "/api/recovery/heatmap/{user}": 4,
    "/api/recovery/recommendations/{user}?date={today}": 40,
}


def count_queries(client, path):
    statements = []

    def before(conn, cursor, statement, *args):
        statements.append(statement)

    event.listen(db.engine, "before_cursor_execute", before)
    try:
        response = client.get(path)
    finally:
        event.remove(db.engine, "before_cursor_execute", before)
    assert response.status_code == 200, (path, response.get_json())
    return len(statements)


def add_day(user_id, day, exercise_ids, *, with_session=True):
    for category in ("breakfast", "lunch", "dinner"):
        meal = Meal(user_id=user_id, date=day, name=category, category=category, total_calories=400)
        db.session.add(meal)
        db.session.flush()
        for name in ("Rice", "Chicken"):
            db.session.add(MealItem(meal_id=meal.id, name=name, calories=200, protein=10, fat=5, carbs=20))
    if with_session:
        started = dt.datetime.combine(day, dt.time(8))
        session = TrainingSession(
            user_id=user_id, started_at=started, finished_at=started + dt.timedelta(hours=1),
            status="finished", internal_load=150,
        )
        db.session.add(session)
        db.session.flush()
        for exercise_id in exercise_ids:
            db.session.add(SessionExercise(
                session_id=session.id, exercise_id=exercise_id, sets_done=3, reps_done=8, load_done=40,
            ))


@pytest.fixture
def busy_user(client, user):
    for item in load_exercise_catalog():
        db.session.add(Exercise(**item))
    db.session.commit()
    client.post("/auth/login", data={"email": user.email, "password": "password123"})
    return user


def measure(client, user):
    return {
        path: count_queries(client, path.format(user=user.id, today=TODAY.isoformat()))
        for path in BUDGETS
    }


def test_queries_stay_within_budget_and_do_not_grow_with_history(client, busy_user):
    exercise_ids = [e.id for e in Exercise.query.order_by(Exercise.id).limit(4)]
    user_id = busy_user.id
    add_day(user_id, TODAY, exercise_ids)
    for days_ago in range(1, 4):
        add_day(user_id, TODAY - dt.timedelta(days=days_ago), exercise_ids)
    db.session.commit()
    # Some reads store what they compute (GET /recovery/recommendations
    # saves the day's snapshot): one pass first, so both measurements see
    # the same stored state and differ only in history.
    measure(client, busy_user)
    short_history = measure(client, busy_user)

    for days_ago in range(4, 60):
        add_day(user_id, TODAY - dt.timedelta(days=days_ago), exercise_ids, with_session=days_ago % 2 == 0)
    db.session.commit()
    long_history = measure(client, busy_user)

    for path, budget in BUDGETS.items():
        assert long_history[path] <= budget, (path, long_history[path])
        assert long_history[path] == short_history[path], (path, short_history[path], long_history[path])
