"""Malformed requests against every API route never become a 500.

A client can send any JSON and any query string. The answer may be 200, 400,
404 and so on, whatever the route decides, but a crash means an input path
that nobody validated. The sweep runs over the URL map, so a new route is
covered without touching this file. Requests start from a valid body on real
rows and break one field at a time, so they get past the first checks.
"""

import datetime as dt

import pytest

from backend.app.extensions import db
from backend.app.models import Dish, DishItem, Meal, MealItem, Product, ProductName
from backend.app.models.recovery.habit import RecoveryHabit
from backend.app.models.recovery.user_habit import UserRecoveryHabit
from backend.app.models.training_session import TrainingSession
from backend.app.training.exercises.catalog import load_exercise_catalog
from backend.app.training.models.exercise import Exercise
from backend.app.training.models.training_plan import TrainingPlan
from backend.app.utils import clock

NON_OBJECT_BODIES = [[1, 2, 3], ["x"], [], "text", 123, True, None]

WRONG_VALUES = [
    [1],
    {"a": 1},
    "not-a-value",
    "NaN",
    "Infinity",
    "²",
    -1,
    0,
    10**30,
    10**400,
    True,
]

QUERY_VALUES = ["abc", "-1", "99999999999999999999999", "NaN", "%00", "2026-13-45", "²"]
QUERY_NAMES = "year limit offset page per_page date days locale q sort category".split()

# Signed by the bot and tested against their own contract; /api/v1/ shares its
# views with /api/. Withdrawing consent would lock the test user out.
SKIPPED_PREFIXES = ("/api/telegram", "/api/v1/")
SKIPPED = {("DELETE", "/api/consent")}


@pytest.fixture
def signed_in(client, user):
    client.post("/auth/login", data={"email": user.email, "password": "password123"})
    return client


@pytest.fixture
def rows(app, user):
    """One real row of everything the routes look up."""
    app.config["OFF_ENABLED"] = False
    for item in load_exercise_catalog():
        db.session.add(Exercise(**item))
    bench = Exercise.query.filter_by(slug="bench-press").one() if db.session.flush() is None else None

    product = Product(
        owner_user_id=user.id,
        source="user",
        normalized_name="soup",
        category="other",
        kcal_per_100g=100,
        protein_per_100g=1,
        fat_per_100g=1,
        carbs_per_100g=1,
        liquid_ml_per_100g=0,
        default_unit="g",
        grams_per_unit=1,
        is_active=True,
    )
    db.session.add(product)
    db.session.flush()
    db.session.add(ProductName(product_id=product.id, locale="en", name="Soup", normalized_name="soup"))

    meal = Meal(user_id=user.id, date=clock.today(), name="lunch", category="lunch")
    db.session.add(meal)
    db.session.flush()
    entry = MealItem(meal_id=meal.id, product_id=product.id, name="Soup", amount=100, unit="g", calories=100)
    db.session.add(entry)

    dish = Dish(user_id=user.id, name="Stew", normalized_name="stew", use_count=0)
    db.session.add(dish)
    db.session.flush()
    db.session.add(DishItem(dish_id=dish.id, product_id=product.id, amount=100, unit="g", position=0))

    session = TrainingSession(user_id=user.id, status="active", started_at=dt.datetime.utcnow())
    plan = TrainingPlan(
        user_id=user.id,
        name="Plan",
        is_active=True,
        days={"mon": {"exercises": [{"exercise": {"id": bench.id}, "sets": 3, "reps": "8"}]}},
    )
    habit = RecoveryHabit(slug="walk", name="Walk", category="movement", points=1, icon="x")
    db.session.add_all([session, plan, habit])
    db.session.flush()
    user_habit = UserRecoveryHabit(user_id=user.id, habit_id=habit.id)
    db.session.add(user_habit)
    db.session.commit()

    return {
        "user_id": user.id,
        "meal_id": meal.id,
        "item_id": entry.id,
        "product_id": product.id,
        "dish_id": dish.id,
        "session_id": session.id,
        "plan_id": plan.id,
        "habit_id": habit.id,
        "user_habit_id": user_habit.id,
        "exercise_id": bench.id,
        "day": "mon",
        "code": "4820000000000",
        "locale": "en",
        "namespace": "common",
        "date": "2026-01-15",
        "date_iso": "2026-01-15",
        "date_string": "2026-01-15",
    }


def _valid_body(rows):
    entry = {"product_id": rows["product_id"], "amount": 100, "unit": "g"}
    exercise = {"exercise": {"id": rows["exercise_id"]}, "sets": 3, "reps": "8", "load": 20, "rpe": 7}
    return {
        # nutrition
        "name": "Thing",
        "locale": "en",
        "meal_id": rows["meal_id"],
        "product_id": rows["product_id"],
        "dish_id": rows["dish_id"],
        "amount": 1,
        "unit": "g",
        "items": [entry],
        "date": clock.today().isoformat(),
        "time": "12:30",
        "category": "lunch",
        "calories": 100,
        "protein": 1,
        "fat": 1,
        "carbs": 1,
        "fiber": 1,
        "weight": 70,
        "favorite": True,
        "return": "day",
        "kcal_per_100g": 100,
        "protein_per_100g": 1,
        "fat_per_100g": 1,
        "carbs_per_100g": 1,
        "fiber_per_100g": 1,
        "sugar_per_100g": 1,
        "saturated_fat_per_100g": 1,
        "salt_per_100g": 1,
        "liquid_ml_per_100g": 0,
        "default_unit": "g",
        "grams_per_unit": 1,
        "brand": "Brand",
        "barcode": "4820000000000",
        # training
        "exercises": [exercise],
        "days": {"mon": {"exercises": [exercise]}},
        "is_active": True,
        "training_days": 3,
        "session_id": rows["session_id"],
        "strict": True,
        "fatigue_before": 3,
        "fatigue_after": 3,
        "sets_done": 3,
        "reps_done": "8",
        "duration_sec_done": 30,
        "load_done": 20,
        "rpe": 7,
        "rir": 2,
        "set_entries": [{"reps": 8, "load": 20}],
        "exercise_id": rows["exercise_id"],
        "pushups": 1,
        "squats": 1,
        "situps": 1,
        # recovery
        "sleep_start": "2026-01-14T23:00:00",
        "sleep_end": "2026-01-15T07:00:00",
        "user_habit_id": rows["user_habit_id"],
        # profile
        "equipment_id": 1,
        "injuries": [],
        "training_location": "home",
        "wants_nutrition": True,
        "wants_recovery": True,
        "primary_goal": "maintenance",
        "focus_upper": 1,
        "focus_lower": 1,
        "focus_core": 1,
    }


def _rules(app):
    for rule in app.url_map.iter_rules():
        if rule.rule.startswith("/api/") and not rule.rule.startswith(SKIPPED_PREFIXES):
            yield rule


def _path(rule, rows):
    path = rule.rule
    for name in rule._converters:
        value = rows.get(name, "not-a-thing")
        path = path.replace(f"<int:{name}>", str(value)).replace(f"<{name}>", str(value))
    return path


def _crashes(app, client, rows):
    crashes = []
    body = _valid_body(rows)

    def check(method, path, what, **request):
        response = client.open(path, method=method, **request)
        # The tests keep one app context, so a failed flush would otherwise
        # leak into the next request; production gets a new session per request.
        db.session.rollback()
        if response.status_code >= 500:
            crashes.append(f"{method} {path} {what!r} -> {response.status_code}")

    # Deleting comes last: the other requests need the rows.
    calls = sorted(
        ((method, _path(rule, rows)) for rule in _rules(app) for method in rule.methods - {"HEAD", "OPTIONS"}),
        key=lambda call: (call[0] == "DELETE", call),
    )
    for method, path in calls:
        if (method, path) in SKIPPED:
            continue
        if method == "GET":
            for name in QUERY_NAMES:
                for value in QUERY_VALUES:
                    check(method, path, {name: value}, query_string={name: value})
            continue
        for non_object in NON_OBJECT_BODIES:
            check(method, path, non_object, json=non_object)
        for field in body:
            for value in WRONG_VALUES:
                check(method, path, {field: value}, json={**body, field: value})
    return crashes


def test_no_route_crashes_on_malformed_input(app, signed_in, rows):
    crashes = _crashes(app, signed_in, rows)
    assert not crashes, "\n".join(crashes[:500]) + f"\n... {len(crashes)} in total"


def test_a_non_object_body_is_a_clear_error(signed_in):
    response = signed_in.post("/api/nutrition/water", json=[1, 2, 3])

    assert response.status_code == 400
    assert response.get_json()["code"] == "invalid_input"


def test_a_non_object_body_never_clears_saved_data(signed_in):
    """A list used to count as an empty request: POST /api/injuries/user with
    any list wiped the user's injuries."""
    response = signed_in.post("/api/injuries/user", json=["anything"])

    assert response.status_code == 400


def test_huge_numbers_in_json_are_invalid(signed_in):
    """1e999 parses as Infinity, past the NaN/Infinity literal check."""
    response = signed_in.post(
        "/api/nutrition/water",
        data='{"amount": 1e999}',
        content_type="application/json",
    )

    assert response.status_code == 400
