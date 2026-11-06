"""Saves that must not lose data: repeated requests, poisoned rows, partial writes."""

import datetime as dt
from concurrent.futures import ThreadPoolExecutor

import pytest

from backend.app.extensions import db
from backend.app.models import Dish, Meal, MealItem, Product, ProductName
from backend.app.models.nutrition.user_water import UserWater
from backend.app.models.nutrition.user_weight import UserWeight
from backend.app.models.training_session import SessionExercise, TrainingSession
from backend.app.services.nutrition import meal_service
from backend.app.services.training.session_service import TrainingSessionService
from backend.app.training.exercises.catalog import load_exercise_catalog
from backend.app.training.models.exercise import Exercise
from backend.app.training.models.performance_state import PerformanceState
from backend.app.training.models.training_plan import TrainingPlan
from backend.app.utils import clock


@pytest.fixture
def signed_in(client, user):
    client.post("/auth/login", data={"email": user.email, "password": "password123"})
    return client


@pytest.fixture
def catalog(app):
    for item in load_exercise_catalog():
        db.session.add(Exercise(**item))
    db.session.commit()
    return {row.slug: row for row in Exercise.query.all()}


def own_product(user, name="Soup", grams_per_unit=1.0, default_unit="g"):
    product = Product(
        owner_user_id=user.id,
        source="user",
        normalized_name=name.lower(),
        category="other",
        kcal_per_100g=100,
        protein_per_100g=1,
        fat_per_100g=1,
        carbs_per_100g=1,
        liquid_ml_per_100g=0,
        default_unit=default_unit,
        grams_per_unit=grams_per_unit,
        is_active=True,
    )
    db.session.add(product)
    db.session.flush()
    db.session.add(ProductName(product_id=product.id, locale="en", name=name, normalized_name=name.lower()))
    db.session.commit()
    return product


def in_threads(app, client, calls):
    """Run ``calls`` at once on one signed-in browser session, as gunicorn's threads would."""
    cookie = client.get_cookie("session").value

    def run(call):
        other = app.test_client()
        other.set_cookie("session", cookie)
        return call(other).status_code

    with ThreadPoolExecutor(max_workers=len(calls)) as pool:
        return list(pool.map(run, calls))


# --- water ---------------------------------------------------------------------------------


def test_quick_water_taps_all_count(app, signed_in):
    statuses = in_threads(
        app,
        signed_in,
        [lambda client: client.post("/api/nutrition/water", json={"amount": 0.25})] * 8,
    )

    assert statuses == [200] * 8
    db.session.rollback()
    assert db.session.query(UserWater).one().amount == pytest.approx(2.0)


@pytest.mark.parametrize("amount", ["NaN", "nan", "Infinity", "-Infinity", True, None, [1], {"a": 1}, 10**400])
def test_water_amount_must_be_a_real_number(signed_in, amount):
    assert signed_in.post("/api/nutrition/water", json={"amount": 0.5}).status_code == 200

    response = signed_in.post("/api/nutrition/water", json={"amount": amount})

    assert response.status_code == 400
    assert response.get_json()["code"] == "invalid_water"
    # "NaN" used to pass the range check and reset the day's water to zero.
    assert signed_in.get("/api/nutrition/water").get_json()["amount"] == pytest.approx(0.5)


def test_water_correction_stops_at_zero_and_keeps_rounding(signed_in):
    signed_in.post("/api/nutrition/water", json={"amount": 0.1})
    signed_in.post("/api/nutrition/water", json={"amount": 0.2})
    assert db.session.query(UserWater).one().amount == pytest.approx(0.3)

    signed_in.post("/api/nutrition/water", json={"amount": -5})
    db.session.expire_all()
    assert db.session.query(UserWater).one().amount == 0.0


def test_first_water_of_a_day_can_be_a_correction(signed_in):
    response = signed_in.post("/api/nutrition/water", json={"amount": -0.5})

    assert response.status_code == 200
    assert response.get_json()["amount"] == 0.0


# --- weight --------------------------------------------------------------------------------


def test_repeated_weight_requests_keep_one_row(app, signed_in, user):
    user_id = user.id
    statuses = in_threads(
        app,
        signed_in,
        [lambda client: client.post("/api/nutrition/weight", json={"weight": 80.5})] * 6,
    )

    assert statuses == [200] * 6
    db.session.rollback()
    assert db.session.query(UserWeight).filter_by(user_id=user_id).one().weight == 80.5


# --- dishes --------------------------------------------------------------------------------


def test_dish_over_the_entry_limit_is_rejected_before_it_is_stored(signed_in, user):
    """100 pieces of a 500 g product pass the per-unit limit but are 50 kg.

    Such a dish used to be stored, then break every later read of the list.
    """
    product = own_product(user, grams_per_unit=500, default_unit="pcs")

    response = signed_in.post(
        "/api/nutrition/dishes",
        json={"name": "Big", "items": [{"product_id": product.id, "amount": 100, "unit": "pcs"}]},
    )

    assert response.status_code == 400
    assert response.get_json()["code"] == "invalid_entry"
    assert Dish.query.count() == 0
    assert signed_in.get("/api/nutrition/dishes").status_code == 200


def test_editing_a_product_cannot_break_the_dishes_that_use_it(signed_in, user):
    product = own_product(user, grams_per_unit=50, default_unit="pcs")
    dish = signed_in.post(
        "/api/nutrition/dishes",
        json={"name": "Stew", "items": [{"product_id": product.id, "amount": 100, "unit": "pcs"}]},
    ).get_json()

    edited = signed_in.patch(f"/api/nutrition/products/{product.id}", json={"grams_per_unit": 500})
    assert edited.status_code == 200

    listed = signed_in.get("/api/nutrition/dishes")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.get_json()["dishes"]] == [dish["id"]]
    assert signed_in.get(f"/api/nutrition/dishes/{dish['id']}").status_code == 200

    # Logging it as saved is what the limit is for: no 50 kg entry.
    logged = signed_in.post("/api/nutrition/log", json={"category": "lunch", "dish_id": dish["id"]})
    assert logged.status_code == 400
    assert logged.get_json()["code"] == "invalid_entry"
    assert MealItem.query.count() == 0


# --- copying yesterday -----------------------------------------------------------------------


def test_copy_yesterday_is_all_or_nothing(signed_in, user, monkeypatch):
    yesterday = clock.today() - dt.timedelta(days=1)
    for category in ("breakfast", "lunch"):
        meal = Meal(user_id=user.id, date=yesterday, name=category, category=category)
        db.session.add(meal)
        db.session.flush()
        db.session.add(MealItem(meal_id=meal.id, name="Rice", calories=100, protein=1, fat=1, carbs=1))
    db.session.commit()

    real = meal_service.recalc_meal_totals
    calls = []

    def fail_on_second(meal):
        calls.append(meal)
        if len(calls) == 2:
            raise RuntimeError("database went away")
        real(meal)

    monkeypatch.setattr(meal_service, "recalc_meal_totals", fail_on_second)
    assert signed_in.post("/api/nutrition/copy-yesterday").status_code == 500
    db.session.rollback()
    assert Meal.query.filter_by(user_id=user.id, date=clock.today()).count() == 0

    monkeypatch.setattr(meal_service, "recalc_meal_totals", real)
    response = signed_in.post("/api/nutrition/copy-yesterday")
    assert response.get_json() == {"status": "ok", "copied": 2}
    copies = Meal.query.filter_by(user_id=user.id, date=clock.today()).all()
    assert sorted(meal.total_calories for meal in copies) == [100, 100]


# --- workouts ------------------------------------------------------------------------------


def workout_item(exercise, **values):
    return {"exercise": {"id": exercise.id}, **values}


def save_workout(client, items, **body):
    return client.post("/api/training/sessions/complete", json={"exercises": items, **body})


def test_a_failed_workout_save_leaves_nothing_behind(signed_in, user, catalog, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("database went away")

    monkeypatch.setattr(TrainingSessionService, "_compute_session_load", staticmethod(fail))
    response = save_workout(signed_in, [workout_item(catalog["bench-press"], sets=3, reps=10, load=60)])

    assert response.status_code == 500
    db.session.rollback()
    assert TrainingSession.query.count() == 0
    assert SessionExercise.query.count() == 0


def test_a_failed_save_over_todays_session_keeps_it(signed_in, user, catalog, monkeypatch):
    bench = catalog["bench-press"]
    first = save_workout(signed_in, [workout_item(bench, sets=3, reps=10, load=60)]).get_json()

    def fail(*args, **kwargs):
        raise RuntimeError("database went away")

    monkeypatch.setattr(TrainingSessionService, "_compute_session_load", staticmethod(fail))
    plank = workout_item(catalog["plank"], sets=2, duration_sec=30)
    response = save_workout(signed_in, [plank], session_id=first["id"])

    assert response.status_code == 500
    db.session.rollback()
    db.session.expire_all()
    rows = SessionExercise.query.filter_by(session_id=first["id"]).all()
    assert [row.exercise_id for row in rows] == [bench.id]


def test_finishing_counts_the_load_once(signed_in, user, catalog):
    saved = save_workout(signed_in, [workout_item(catalog["bench-press"], sets=3, reps=10, load=60)]).get_json()

    session = db.session.get(TrainingSession, saved["id"])
    assert session.status == "finished"
    assert session.internal_load > 0
    performance = PerformanceState.query.filter_by(user_id=user.id).one()
    assert performance.training_load == pytest.approx(session.internal_load)


def test_an_exercise_listed_twice_keeps_all_its_sets(signed_in, user, catalog):
    bench = catalog["bench-press"]
    saved = save_workout(
        signed_in,
        [
            workout_item(bench, set_entries=[{"reps": 10, "load": 60}, {"reps": 8, "load": 70}]),
            workout_item(bench, set_entries=[{"reps": 6, "load": 80}], rpe=9),
        ],
    )

    assert saved.status_code == 200
    row = SessionExercise.query.filter_by(exercise_id=bench.id).one()
    assert [entry["reps"] for entry in row.set_entries] == [10, 8, 6]
    assert row.sets_done == 3
    assert row.rpe == 9


def test_an_exercise_listed_twice_without_per_set_values_adds_up_sets(signed_in, user, catalog):
    bench = catalog["bench-press"]
    save_workout(
        signed_in,
        [workout_item(bench, sets=3, reps=10, load=60), workout_item(bench, sets=2, reps=10, load=60)],
    )

    assert SessionExercise.query.filter_by(exercise_id=bench.id).one().sets_done == 5


def test_sets_measured_the_wrong_way_are_rejected(signed_in, catalog):
    response = save_workout(
        signed_in, [workout_item(catalog["plank"], set_entries=[{"reps": 10, "load": 0}])]
    )
    assert response.status_code == 400

    response = save_workout(
        signed_in, [workout_item(catalog["bench-press"], set_entries=[{"duration_sec": 30, "load": 10}])]
    )
    assert response.status_code == 400


def test_rir_null_does_not_erase_a_logged_rpe(signed_in, catalog):
    save_workout(
        signed_in, [workout_item(catalog["bench-press"], sets=3, reps=10, load=60, rpe=7.5, rir=None)]
    )

    assert SessionExercise.query.one().rpe == 7.5


def test_rir_alone_still_sets_or_clears_the_rating(signed_in, catalog):
    bench = catalog["bench-press"]
    saved = save_workout(signed_in, [workout_item(bench, sets=3, reps=10, load=60, rir=2)]).get_json()
    assert SessionExercise.query.one().rpe == 8.0

    save_workout(signed_in, [workout_item(bench, sets=3, reps=10, load=60, rir=None)], session_id=saved["id"])
    db.session.expire_all()
    assert SessionExercise.query.one().rpe is None


def test_saving_a_workout_runs_the_same_queries_for_any_number_of_exercises(signed_in, user, catalog):
    """Saving recomputed the session figures three times and committed per exercise."""
    from sqlalchemy import event

    slugs = sorted(catalog)
    few = [workout_item(catalog[slug], sets=3, reps=10, load=20) for slug in slugs[:2]]
    many = [workout_item(catalog[slug], sets=3, reps=10, load=20) for slug in slugs[:10]]
    save_workout(signed_in, few)  # fills the catalog cache

    def count(items):
        statements = []

        def before(conn, cursor, statement, *args):
            statements.append(statement)

        event.listen(db.engine, "before_cursor_execute", before)
        try:
            assert save_workout(signed_in, items).status_code == 200
        finally:
            event.remove(db.engine, "before_cursor_execute", before)
        return len(statements)

    few_count, many_count = count(few), count(many)
    assert many_count == few_count
    assert many_count <= 22


# --- plans ---------------------------------------------------------------------------------


@pytest.mark.parametrize("days", [{}, None, {"mon": ["not", "a", "day"]}, {"mon": {"exercises": ["x"]}}])
@pytest.mark.parametrize("path", ["/api/training/today", "/api/training/today-session"])
def test_todays_workout_survives_an_odd_stored_plan(signed_in, user, path, days):
    db.session.add(TrainingPlan(user_id=user.id, name="Old", is_active=True, days=days))
    db.session.commit()

    response = signed_in.get(path)

    assert response.status_code == 200
    assert response.get_json()["exercises"] == []


def test_todays_workout_reads_a_plan_with_bare_day_lists(signed_in, user, catalog):
    key = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"][clock.today().weekday()]
    bench = catalog["bench-press"]
    db.session.add(
        TrainingPlan(
            user_id=user.id,
            name="Old",
            is_active=True,
            days={key: [{"exercise": {"id": bench.id}, "sets": 4, "reps": "8"}]},
        )
    )
    db.session.commit()

    exercises = signed_in.get("/api/training/today-session").get_json()["exercises"]

    assert [(item["exercise"]["id"], item["sets"]) for item in exercises] == [(bench.id, 4)]
