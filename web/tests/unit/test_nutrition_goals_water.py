"""Calorie and macro targets, the water goal and fluid logging, the clock.

Expected numbers are worked out by hand (the arithmetic is in the test or in
a comment) rather than by calling the helpers under test.
"""
import datetime as dt
import math
import re
import threading
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import event

from backend.app.extensions import db
from backend.app.models import (
    Meal,
    MealItem,
    NutritionGoalHistory,
    UserGoals,
    UserProfile,
    UserWater,
    UserWeight,
)
from backend.app.services.nutrition import calories_service as cal
from backend.app.services.nutrition import goals_service, water_service
from backend.app.services.nutrition.day_service import get_daily_nutrition_data
from backend.app.services.nutrition.stats_service import get_day_details
from backend.app.services.nutrition.weight_service import update_user_weight
from backend.app.services.dashboard import aggregator
from backend.app.utils import clock

KYIV = ZoneInfo("Europe/Kyiv")


def person(weight=80, height=180, age=30, gender="male", activity="moderate", goal="maintenance"):
    return SimpleNamespace(profile=SimpleNamespace(
        weight=weight, height=height, age=age, gender=gender, activity=activity, goal=goal,
    ))


def add_profile(user, **values):
    base = dict(training_location="home", weight=80, height=180, age=30, gender="male",
                activity="moderate", goal="maintenance")
    base.update(values)
    profile = UserProfile(user_id=user.id, **base)
    db.session.add(profile)
    db.session.commit()
    return profile


# --- calories and macros --------------------------------------------------

# Mifflin-St Jeor by hand: 10*kg + 6.25*cm - 5*age + (5 men | -161 women).
#   M 80 kg 180 cm 30 y: 800 + 1125 - 150 + 5 = 1780 -> x1.55 = 2759
#     protein 1.6*80 = 128 g (512 kcal); fat 28% = 772.5 kcal = 85.8 g;
#     carbs (2759-512-772.5)/4 = 368.6 g (53% of energy, inside 45-65%)
#   F 60 kg 165 cm 28 y: 600 + 1031.25 - 140 - 161 = 1330.25 -> x1.375 = 1829
#     protein 96 g; fat 512.1 kcal = 56.9 g; carbs 233.2 g
#   F 50 kg 160 cm 25 y sedentary, fat loss: 500 + 1000 - 125 - 161 = 1214
#     -> x1.2 = 1456.8 -> x0.85 = 1238; protein 2.0*50 = 100 g (400 kcal);
#     fat 28% would leave carbs at 39.7% (< 45%), so fat gives way to 20.2%+
#     until carbs reach 45%: fat 31.2 g, carbs 139.3 g
GOAL_CASES = [
    (dict(), dict(calories=2759, protein=128.0, fat=85.8, carbs=368.6)),
    (dict(weight=60, height=165, age=28, gender="female", activity="light"),
     dict(calories=1829, protein=96.0, fat=56.9, carbs=233.2)),
    (dict(weight=50, height=160, age=25, gender="female", activity="sedentary", goal="fat_loss"),
     dict(calories=1238, protein=100.0, fat=31.2, carbs=139.3)),
]


@pytest.mark.parametrize("profile, expected", GOAL_CASES)
def test_goals_for_representative_profiles(profile, expected):
    goals = cal.calculate_nutrition_goals(person(**profile))
    assert goals["calories"] == expected["calories"]
    for macro in ("protein", "fat", "carbs"):
        assert goals[macro] == pytest.approx(expected[macro], abs=0.05)


def test_unspecified_sex_uses_the_midpoint_constant():
    # base - 78 sits between the men's +5 and the women's -161.
    # 10*70 + 6.25*170 - 5*40 = 1562.5; -78 -> 1484.5; x1.55 = 2301.0
    assert cal.calculate_calories(person(weight=70, height=170, age=40, gender=None)) == 2301
    assert cal.calculate_calories(person(weight=70, height=170, age=40, gender="other")) == 2301


@pytest.mark.parametrize(
    "activity, factor",
    [("sedentary", 1.20), ("light", 1.375), ("moderate", 1.55), ("active", 1.725),
     ("very_active", 1.90), ("ACTIVE", 1.725), ("1.3", 1.3), (None, 1.55),
     ("couch", 1.55), (5, 1.55), ("0.5", 1.55)],
)
def test_activity_factors(activity, factor):
    assert cal.get_activity_factor(activity) == pytest.approx(factor)


@pytest.mark.parametrize(
    "raw, canonical",
    [("fat_loss", "cut"), ("lose", "cut"), ("muscle_gain", "gain"), ("strength", "strength"),
     ("recomp", "recomp"), ("maintenance", "maintenance"), ("lean_gain", "lean_gain"),
     ("???", "maintenance"), (None, "maintenance")],
)
def test_goal_vocabulary(raw, canonical):
    assert cal.get_goal(person(goal=raw)) == canonical


@pytest.mark.parametrize(
    "goal, adjustment", [("fat_loss", -0.15), ("maintenance", 0), ("recomp", 0),
                         ("strength", 0.05), ("lean_gain", 0.08), ("muscle_gain", 0.10)],
)
def test_goal_adjusts_the_calories(goal, adjustment):
    # TDEE of the 80 kg man above = 1780 * 1.55 = 2759
    assert cal.calculate_calories(person(goal=goal)) == round(2759 * (1 + adjustment))


def test_calorie_floors_and_ceiling():
    # 45 kg woman, 150 cm, 40 y, sedentary, fat loss: 1026.5 * 1.2 * 0.85 = 1047 -> 1200
    assert cal.calculate_calories(person(45, 150, 40, "female", "sedentary", "fat_loss")) == 1200
    # 50 kg man, 150 cm, 60 y: 1142.5 * 1.2 * 0.85 = 1165 -> 1500
    assert cal.calculate_calories(person(50, 150, 60, "male", "sedentary", "fat_loss")) == 1500
    # Unspecified sex floor 1350
    assert cal.calculate_calories(person(45, 150, 40, None, "sedentary", "fat_loss")) == 1350
    # 300 kg, 230 cm, 20 y, active, gain would be 8239: capped at 6000
    assert cal.calculate_calories(person(300, 230, 20, "male", "active", "muscle_gain")) == 6000


@pytest.mark.parametrize(
    "profile",
    [dict(weight=None), dict(height=None), dict(age=None),
     dict(weight=29.9), dict(weight=300.1), dict(height=119), dict(height=231),
     dict(age=14), dict(age=101), dict(weight=-70), dict(weight=0)],
)
def test_an_incomplete_or_out_of_range_profile_has_no_goals(profile):
    assert cal.calculate_nutrition_goals(person(**profile)) is None
    assert cal.calculate_calories(person(**profile)) is None


def test_limits_of_the_valid_profile_range():
    assert cal.calculate_nutrition_goals(person(weight=30, height=120, age=15)) is not None
    assert cal.calculate_nutrition_goals(person(weight=300, height=230, age=100)) is not None


def test_protein_never_exceeds_a_third_of_energy_plus_the_ceiling():
    # 150 kg man, 190 cm, 40 y, moderate, fat loss:
    # BMR 1500 + 1187.5 - 200 + 5 = 2492.5; x1.55 = 3863.4; x0.85 = 3283.8 -> 3284
    # 2 g/kg = 300 g = 1200 kcal = 36.5% > 35%: capped at 3284*0.35/4 = 287.4 g
    goals = cal.calculate_nutrition_goals(person(150, 190, 40, "male", "moderate", "fat_loss"))
    assert goals["calories"] == 3284
    assert goals["protein"] == pytest.approx(287.35, abs=0.06)
    assert goals["protein"] * 4 <= 0.35 * goals["calories"] + 0.3


def build_profiles():
    for gender in ("male", "female", "other", None):
        for age in (15, 22, 35, 50, 70, 100):
            for weight, height in ((30, 120), (45, 155), (60, 165), (80, 180), (110, 190), (160, 200), (300, 230)):
                for activity in ("sedentary", "light", "moderate", "active", None):
                    for goal in ("fat_loss", "maintenance", "muscle_gain", "strength", "recomp", None):
                        yield person(weight, height, age, gender, activity, goal)


def test_macro_energy_reconciles_with_the_calorie_target_for_every_profile():
    checked = 0
    worst = 0.0
    for who in build_profiles():
        goals = cal.calculate_nutrition_goals(who)
        assert goals is not None
        energy = goals["protein"] * 4 + goals["fat"] * 9 + goals["carbs"] * 4
        # Each macro is rounded to 0.1 g: at most 0.2 + 0.45 + 0.2 kcal.
        assert abs(energy - goals["calories"]) <= 1.0, (who.profile, goals, energy)
        assert goals["protein"] > 0 and goals["fat"] > 0 and goals["carbs"] > 0
        assert goals["protein"] * 4 <= 0.35 * goals["calories"] + 1.0
        assert goals["fat"] * 9 >= 0.20 * goals["calories"] - 1.0
        assert goals["fat"] * 9 <= 0.35 * goals["calories"] + 1.0
        worst = max(worst, abs(energy - goals["calories"]))
        checked += 1
    assert checked > 5000 and worst <= 1.0


def test_goal_calculation_is_deterministic():
    who = person(77.7, 178.5, 33, "male", "light", "strength")
    assert cal.calculate_nutrition_goals(who) == cal.calculate_nutrition_goals(who)


# --- goals are read without writing, and their history --------------------

class StatementLog:
    def __init__(self):
        self.writes = []

    def __call__(self, conn, cursor, statement, *args):
        if statement.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
            self.writes.append(statement.split()[0] + " " + statement.split()[2 if statement.upper().startswith("INSERT") else 1])


def test_reading_goals_never_writes(app, user):
    add_profile(user)
    db.session.expire_all()
    log = StatementLog()
    event.listen(db.engine, "before_cursor_execute", log)
    try:
        goals = goals_service.get_goals(user.id)
        get_daily_nutrition_data(user.id)
    finally:
        event.remove(db.engine, "before_cursor_execute", log)
    assert goals["available"] is True and goals["calories"] == 2759
    assert log.writes == []
    assert UserGoals.query.count() == 0   # reading did not create the row either


def test_goals_without_a_complete_profile_are_unavailable_not_zero_targets(app, user):
    assert goals_service.get_goals(user.id) == {
        "calories": 0, "protein": 0, "fat": 0, "carbs": 0, "fiber": 30.0,
        "available": False, "source": "none",
    }
    add_profile(user, weight=None)
    unavailable = goals_service.get_goals(user.id)
    assert unavailable["available"] is False and unavailable["calories"] == 0
    assert goals_service.get_goals(999999)["available"] is False


def test_last_stored_goals_stay_visible_when_the_profile_can_no_longer_give_goals(app, user):
    add_profile(user, weight=None)
    db.session.add(UserGoals(user_id=user.id, calories_goal=2200, protein_goal=150, fat_goal=70,
                             carb_goal=250, fiber_goal=28))
    db.session.commit()
    goals = goals_service.get_goals(user.id)
    assert goals["available"] is True and goals["source"] == "stored"
    assert (goals["calories"], goals["protein"], goals["fiber"]) == (2200, 150, 28)


def test_a_profile_change_records_the_new_goals_once_per_day(app, user, monkeypatch):
    day1 = dt.datetime(2024, 5, 1, 10, 0, tzinfo=KYIV)
    monkeypatch.setattr(clock, "now", lambda: day1)
    profile = add_profile(user)                                  # 2759 kcal
    rows = NutritionGoalHistory.query.filter_by(user_id=user.id).all()
    assert [(r.effective_from, r.calories) for r in rows] == [(dt.date(2024, 5, 1), 2759)]

    profile.training_location = "gym"                             # not an input of the goals
    db.session.commit()
    assert NutritionGoalHistory.query.count() == 1

    profile.weight = 85                                           # same day: the row is updated
    db.session.commit()
    rows = NutritionGoalHistory.query.all()
    assert len(rows) == 1 and rows[0].calories == round((10 * 85 + 1125 - 150 + 5) * 1.55)

    monkeypatch.setattr(clock, "now", lambda: day1 + dt.timedelta(days=3))
    profile.goal = "fat_loss"
    db.session.commit()
    rows = NutritionGoalHistory.query.order_by(NutritionGoalHistory.effective_from).all()
    assert [r.effective_from for r in rows] == [dt.date(2024, 5, 1), dt.date(2024, 5, 4)]
    assert rows[1].calories < rows[0].calories

    profile.goal = "fat_loss"                                     # no change: nothing new
    profile.weight = 85
    db.session.commit()
    assert NutritionGoalHistory.query.count() == 2


def test_an_incomplete_profile_records_nothing(app, user):
    add_profile(user, weight=None)
    assert NutritionGoalHistory.query.count() == 0


def test_logging_a_weight_records_the_goal_change(app, user, monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: dt.datetime(2024, 6, 1, 9, 0, tzinfo=KYIV))
    add_profile(user, weight=80)
    monkeypatch.setattr(clock, "now", lambda: dt.datetime(2024, 6, 10, 9, 0, tzinfo=KYIV))
    update_user_weight(user, 78)
    rows = NutritionGoalHistory.query.order_by(NutritionGoalHistory.effective_from).all()
    assert [r.effective_from for r in rows] == [dt.date(2024, 6, 1), dt.date(2024, 6, 10)]
    assert rows[1].calories == round((10 * 78 + 1125 - 150 + 5) * 1.55)


def test_goals_for_a_day_come_from_the_history_never_invented(app, user):
    current = goals_service.get_goals(user.id)
    rows = [
        NutritionGoalHistory(user_id=user.id, effective_from=dt.date(2024, 1, 10), calories=2500,
                             protein=150, fat=80, carbs=300, fiber=30),
        NutritionGoalHistory(user_id=user.id, effective_from=dt.date(2024, 3, 1), calories=2100,
                             protein=140, fat=70, carbs=240, fiber=30),
    ]
    db.session.add_all(rows)
    db.session.commit()
    timeline = goals_service.goals_timeline(user.id, dt.date(2024, 2, 1), dt.date(2024, 4, 1))

    before = goals_service.goals_for_day(timeline, current, dt.date(2024, 1, 1))
    assert before["source"] == "current" and before["estimated"] is True   # nothing stored for it
    assert goals_service.goals_for_day(timeline, current, dt.date(2024, 2, 15))["calories"] == 2500
    assert goals_service.goals_for_day(timeline, current, dt.date(2024, 3, 1))["calories"] == 2100
    on = goals_service.goals_for_day(timeline, current, dt.date(2024, 3, 31))
    assert on["calories"] == 2100 and on["source"] == "history" and on["estimated"] is False


def test_a_past_day_is_compared_with_its_own_targets(app, user):
    add_profile(user, weight=None)  # no current targets at all
    db.session.add_all([
        NutritionGoalHistory(user_id=user.id, effective_from=dt.date(2024, 1, 1), calories=2000,
                             protein=120, fat=60, carbs=250, fiber=30),
        NutritionGoalHistory(user_id=user.id, effective_from=dt.date(2024, 2, 1), calories=3000,
                             protein=180, fat=90, carbs=380, fiber=30),
    ])
    for day in (dt.date(2024, 1, 15), dt.date(2024, 2, 15)):
        meal = Meal(user_id=user.id, date=day, name="x", category="lunch", total_calories=1500)
        db.session.add(meal)
        db.session.flush()
        db.session.add(MealItem(meal_id=meal.id, name="x", calories=1500, protein=0, fat=0, carbs=0))
    db.session.commit()

    january = get_day_details(user.id, dt.date(2024, 1, 15))
    february = get_day_details(user.id, dt.date(2024, 2, 15))
    assert (january["calorie_goal"], january["balance_status"]) == (2000, "under")   # 1500 vs 2000: -25%
    assert (february["calorie_goal"], february["balance_status"]) == (3000, "under")
    assert january["goal_estimated"] is False

    from backend.app.services.nutrition.stats_service import get_year_heatmap

    by_date = {d["date"]: d for d in get_year_heatmap(user.id, 2024)["days"]}
    assert by_date["2024-01-15"]["calorie_goal"] == 2000 and by_date["2024-01-15"]["percent"] == 75
    assert by_date["2024-02-15"]["calorie_goal"] == 3000 and by_date["2024-02-15"]["percent"] == 50
    assert by_date["2024-01-01"]["calorie_goal"] == 2000 and by_date["2024-01-01"]["goal_estimated"] is False
    assert by_date["2024-02-01"]["calorie_goal"] == 3000


# --- water ----------------------------------------------------------------

# 80 kg, 30 y: ml/kg = 36 - (30-25)/15 = 35.667 -> 2.8533 L; men x1.03 = 2.9389
WATER_ACTIVITY_CASES = [
    ("sedentary", 2.94),     # x1.000 = 2.9389
    ("light", 3.01),         # x1.025 = 3.0124
    ("moderate", 3.09),      # x1.050 = 3.0858
    ("active", 3.23),        # x1.100 = 3.2328
    ("very_active", 3.38),   # x1.150 = 3.3797
    (None, 2.94),
    ("unknown-level", 2.94),
]


@pytest.mark.parametrize("activity, liters", WATER_ACTIVITY_CASES)
def test_every_profile_activity_level_changes_the_water_goal_as_documented(activity, liters):
    assert water_service.calculate_water(80, age=30, gender="male", activity=activity) == liters


def test_the_four_profile_activity_levels_are_all_distinct():
    values = [water_service.calculate_water(80, 30, "male", level)
              for level in ("sedentary", "light", "moderate", "active")]
    assert values == sorted(values) and len(set(values)) == 4


@pytest.mark.parametrize(
    "weight, age, gender, activity, liters",
    [
        (60, 28, "female", "light", 2.2),     # 60 * 35.8 = 2.148 L x1.025 = 2.2017
        (70, None, None, None, 2.45),         # missing age: 35 ml/kg -> 2.45
        (70, 200, "male", None, 2.52),        # implausible age counts as missing: 2.45 x1.03 = 2.5235
        (40, 30, "female", None, 1.5),        # 1.427 L: floor
        (150, 30, "male", "active", 3.5),     # 5.4 L: ceiling
        (30, 8, None, None, 1.5),             # 1.35 L: floor
        (100, 15, "female", None, 3.5),       # 100 * (45-3*1.4=40.8)= 4.08 L: ceiling
        (90, 70, "female", None, 2.9),        # 61+: 33 - (70-60)*3/40 = 32.25 ml/kg -> 2.9025 L
    ],
)
def test_water_goal_values(weight, age, gender, activity, liters):
    assert water_service.calculate_water(weight, age, gender, activity) == pytest.approx(liters, abs=0.006)


@pytest.mark.parametrize("weight", [None, 0, -5, "abc", float("nan"), float("inf"), 19.9, 400.1, "x"])
def test_without_a_usable_weight_there_is_no_water_goal_not_zero(weight):
    assert water_service.calculate_water(weight, 30, "male", "active") is None


def test_water_goal_is_rounded_once_at_the_end():
    # 75.3 kg, 33 y, no sex, no activity: 75.3 * (36 - 8/15) = 2.6670... L -> 2.67
    exact = 75.3 * (36 - 8 / 15) / 1000
    assert water_service.calculate_water(75.3, 33) == round(exact, 2) == 2.67


def test_fat_loss_and_gain_goals_do_not_change_the_water_goal(app, user):
    results = set()
    for goal in ("fat_loss", "muscle_gain", "maintenance", None):
        profile = UserProfile.query.filter_by(user_id=user.id).first()
        if profile is None:
            profile = add_profile(user)
        profile.goal = goal
        db.session.commit()
        results.add(water_service.water_goal_for_user(user.id))
    assert results == {3.09}


def test_one_water_goal_everywhere(app, user, client):
    add_profile(user, weight=80, age=30, gender="male", activity="active")
    expected = 3.23
    assert water_service.water_goal_for_user(user.id) == expected
    assert water_service.get_water_data(user.id)["recommended"] == expected
    assert get_daily_nutrition_data(user.id)["water_goal"] == expected
    assert get_day_details(user.id, dt.date.today())["water_goal"] == expected
    client.post("/auth/login", data={"email": user.email, "password": "password123"})
    assert client.get("/api/nutrition/water").get_json()["recommended"] == expected
    assert client.get("/api/nutrition/day").get_json()["water_goal"] == expected


def test_missing_weight_is_reported_as_no_goal_everywhere(app, user, client):
    add_profile(user, weight=None)
    data = water_service.get_water_data(user.id)
    assert data["recommended"] is None and data["recommended_available"] is False
    day = get_daily_nutrition_data(user.id)
    assert day["water_goal"] is None and day["water_percent"] is None
    client.post("/auth/login", data={"email": user.email, "password": "password123"})
    body = client.get("/api/nutrition/water").get_json()
    assert body["recommended"] is None and body["recommended_available"] is False
    assert water_service.get_water_data(999999)["recommended"] is None


def test_a_past_days_goal_uses_the_weight_of_that_day(app, user, monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: dt.datetime(2024, 6, 20, 12, 0, tzinfo=KYIV))
    add_profile(user, weight=70)
    db.session.add_all([
        UserWeight(user_id=user.id, date=dt.date(2024, 6, 1), weight=90),
        UserWeight(user_id=user.id, date=dt.date(2024, 6, 15), weight=80),
    ])
    db.session.commit()
    # 35.667 ml/kg x 1.03 (men) x 1.05 (moderate): 90 kg -> 3.47, 80 kg -> 3.09, 70 kg -> 2.70
    assert water_service.water_goal_for_user(user.id, dt.date(2024, 6, 10)) == pytest.approx(3.47, abs=0.006)
    assert water_service.water_goal_for_user(user.id, dt.date(2024, 6, 16)) == pytest.approx(3.09, abs=0.006)
    assert water_service.water_goal_for_user(user.id, dt.date(2024, 6, 20)) == pytest.approx(2.70, abs=0.006)
    # Before any weighing the profile's weight is the best there is.
    assert water_service.water_goal_for_user(user.id, dt.date(2024, 5, 1)) == pytest.approx(2.70, abs=0.006)


# --- fluid intake and the clock -------------------------------------------

def test_intake_is_manual_water_plus_the_fluid_of_drinks(app, user):
    meal = Meal(user_id=user.id, date=dt.date.today(), name="x", category="snack")
    db.session.add(meal)
    db.session.flush()
    db.session.add(MealItem(meal_id=meal.id, name="milk", calories=100, protein=0, fat=0, carbs=0,
                            liquid_ml=250))
    db.session.commit()
    water_service.add_water_service(user.id, 0.5)
    water_service.add_water_service(user.id, 0.25)
    assert water_service.get_total_fluid_liters(user.id) == 1.0   # 0.75 + 0.25
    assert water_service.add_water_service(user.id, -5).amount == 0.0   # never below zero


def test_water_can_be_logged_for_a_past_day_but_not_the_future(app, user, monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: dt.datetime(2024, 7, 10, 12, 0, tzinfo=KYIV))
    water_service.add_water_service(user.id, 1.5, dt.date(2024, 7, 8))
    assert water_service.get_total_fluid_liters(user.id, dt.date(2024, 7, 8)) == 1.5
    assert water_service.get_total_fluid_liters(user.id) == 0.0
    with pytest.raises(water_service.WaterValidationError):
        water_service.add_water_service(user.id, 1, dt.date(2024, 7, 11))
    with pytest.raises(water_service.WaterValidationError):
        water_service.add_water_service(user.id, 1, dt.date(2023, 7, 10))    # 366 days back
    water_service.add_water_service(user.id, 1, dt.date(2023, 7, 11))        # 365 days: the limit


def test_the_water_api_accepts_an_optional_date(app, user, client, monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: dt.datetime(2024, 7, 10, 12, 0, tzinfo=KYIV))
    client.post("/auth/login", data={"email": user.email, "password": "password123"})
    ok = client.post("/api/nutrition/water", json={"amount": 0.5, "date": "2024-07-09"})
    assert ok.status_code == 200 and ok.get_json()["date"] == "2024-07-09" and ok.get_json()["amount"] == 0.5
    assert client.get("/api/nutrition/water?date=2024-07-09").get_json()["amount"] == 0.5
    assert client.get("/api/nutrition/water").get_json()["amount"] == 0.0
    for bad in ("2024-07-11", "yesterday", "2020-01-01"):
        response = client.post("/api/nutrition/water", json={"amount": 0.5, "date": bad})
        assert response.status_code == 400 and response.get_json()["code"] == "invalid_date"
    assert client.get("/api/nutrition/water?date=nonsense").status_code == 400


def test_the_day_follows_the_application_timezone_not_the_server(app, user, monkeypatch):
    # 23:50 in Kyiv on 10 July is 20:50 UTC; 00:10 on the 11th is 21:10 UTC.
    monkeypatch.setattr(clock, "now", lambda: dt.datetime(2024, 7, 10, 23, 50, tzinfo=KYIV))
    water_service.add_water_service(user.id, 0.5)
    monkeypatch.setattr(clock, "now", lambda: dt.datetime(2024, 7, 11, 0, 10, tzinfo=KYIV))
    water_service.add_water_service(user.id, 0.3)
    assert {w.date: w.amount for w in UserWater.query.all()} == {
        dt.date(2024, 7, 10): 0.5, dt.date(2024, 7, 11): 0.3,
    }
    assert water_service.get_water_data(user.id)["date"] == "2024-07-11"


def test_clock_zone_comes_from_settings(monkeypatch):
    monkeypatch.delenv("APP_TIMEZONE", raising=False)
    monkeypatch.delenv("NOSI_FIT_TIMEZONE", raising=False)
    assert clock.timezone_name() == "Europe/Kyiv"
    monkeypatch.setenv("NOSI_FIT_TIMEZONE", "Europe/Warsaw")
    assert clock.timezone_name() == "Europe/Warsaw"
    monkeypatch.setenv("APP_TIMEZONE", "America/New_York")
    assert clock.timezone_name() == "America/New_York"
    assert str(clock.app_timezone()) == "America/New_York"
    monkeypatch.setenv("APP_TIMEZONE", "Not/AZone")
    assert str(clock.app_timezone()) == "Europe/Kyiv"      # a typo does not break requests


def test_real_clock_is_aware_and_in_the_application_zone(monkeypatch):
    monkeypatch.undo()
    monkeypatch.setenv("APP_TIMEZONE", "Pacific/Auckland")
    moment = clock.now()
    assert moment.tzinfo is not None and moment.utcoffset() in (dt.timedelta(hours=12), dt.timedelta(hours=13))
    assert clock.today() == moment.date()


def test_dashboard_and_nutrition_page_agree_on_water(app, user):
    add_profile(user)
    water_service.add_water_service(user.id, 0.8)
    meal = Meal(user_id=user.id, date=dt.date.today(), name="x", category="snack")
    db.session.add(meal)
    db.session.flush()
    db.session.add(MealItem(meal_id=meal.id, name="tea", calories=0, protein=0, fat=0, carbs=0, liquid_ml=300))
    db.session.add(MealItem(meal_id=meal.id, name="bread", calories=200, protein=6, fat=1, carbs=40))
    meal.total_calories = 200
    db.session.commit()
    page = get_daily_nutrition_data(user.id)["water"]
    dashboard = aggregator.get_today_overview(user.id)["nutrition"]["water"]
    heatmap_today = next(d for d in aggregator.get_heatmap(user.id)["days"] if d["date"] == dt.date.today().isoformat())
    assert page == dashboard == heatmap_today["nutrition"]["water"] == 1.1
    assert math.isclose(water_service.get_water_data(user.id)["amount"], 1.1)
    assert aggregator.get_today_overview(user.id)["nutrition"]["water"] != 0   # the old hardcoded value


# --- the values the forms store ---------------------------------------------

TEMPLATES = Path(__file__).resolve().parents[2] / "app" / "templates"
FORMS = [
    TEMPLATES / "auth" / "register.html",
    TEMPLATES / "auth" / "complete_profile.html",
    TEMPLATES / "app" / "profile" / "modals" / "edit_profile.html",
]


def select_values(path, field):
    """The option values of the <select name="field"> of a template."""
    source = path.read_text(encoding="utf-8")
    start = re.search(rf'<select[^>]*name="{field}"', source)
    if start is None:
        return None
    block = source[start.start(): source.index("</select>", start.start())]
    return [v for v in re.findall(r'value="([^"]*)"', block) if v]


@pytest.mark.parametrize("path", FORMS, ids=lambda p: p.name)
def test_every_activity_value_a_form_stores_is_understood(path):
    values = select_values(path, "activity")
    if values is None:
        pytest.skip("no activity select in this form")
    assert len(values) >= 4
    for value in values:
        assert len(value) <= 10                                   # fits the column
        assert cal.activity_level(value) in cal.ACTIVITY_FACTORS, value
        assert water_service.activity_factor(value) in water_service.ACTIVITY_FACTORS.values()
        # Water and calories read the value the same way.
        assert water_service.ACTIVITY_FACTORS[cal.activity_level(value)] == water_service.activity_factor(value)
    # The forms agree with each other on the order of the levels.
    levels = [cal.activity_level(v) for v in values]
    assert levels == sorted(levels, key=list(cal.ACTIVITY_FACTORS).index)


@pytest.mark.parametrize("path", FORMS, ids=lambda p: p.name)
def test_every_goal_and_sex_value_a_form_stores_is_understood(path):
    for value in select_values(path, "goal") or []:
        assert value in cal.GOAL_ALIASES, value               # mapped on purpose, not by the default
    for value in select_values(path, "gender") or []:
        assert value in ("male", "female", "other"), value


@pytest.mark.parametrize(
    "stored, level",
    [("sedentary", "sedentary"), ("LIGHT", "light"), (" moderate ", "moderate"), ("active", "active"),
     ("1.2", "sedentary"), ("1.375", "light"), ("1.55", "moderate"), ("1.725", "active"), ("1.9", "very_active"),
     (1.55, "moderate"), (1.3, "light"), (1.46, "light"), (1.47, "moderate"), ("very_active", "very_active"),
     (None, None), ("", None), ("couch", None), ("1.0", None), ("2.5", None), (True, None), ([], None)],
)
def test_activity_level_reads_both_storage_formats(stored, level):
    assert cal.activity_level(stored) == level


def test_a_numeric_activity_changes_the_water_goal_like_its_label():
    for numeric, label in (("1.2", "sedentary"), ("1.375", "light"), ("1.55", "moderate"),
                           ("1.725", "active"), ("1.9", "very_active")):
        assert water_service.calculate_water(80, 30, "male", numeric) == \
               water_service.calculate_water(80, 30, "male", label)
    assert water_service.calculate_water(80, 30, "male", "1.9") == 3.38


# --- concurrent saves of one profile (M1) -----------------------------------

_OPEN_SESSIONS = []


@pytest.fixture(autouse=True)
def _close_extra_sessions():
    """Sessions the concurrency tests open are closed even if the test fails.

    An abandoned transaction would keep its locks and make the next test wait
    for them instead of failing on its own.
    """
    yield
    while _OPEN_SESSIONS:
        session = _OPEN_SESSIONS.pop()
        try:
            session.rollback()
        finally:
            session.close()


def _two_sessions(user):
    from sqlalchemy.orm import Session

    first, second = Session(db.engine), Session(db.engine)
    _OPEN_SESSIONS.extend([first, second])
    return (first, first.query(UserProfile).filter_by(user_id=user.id).one(),
            second, second.query(UserProfile).filter_by(user_id=user.id).one())


def _fresh_user_with_profile(user):
    add_profile(user)
    db.session.execute(db.text("DELETE FROM nutrition_goal_history"))
    db.session.commit()


def test_two_simultaneous_saves_both_complete_and_leave_one_row(app, user):
    """The failure this guards: both saves saw no row for today and both inserted."""
    _fresh_user_with_profile(user)
    first, first_profile, second, second_profile = _two_sessions(user)
    outcome = {}

    first_profile.weight = 70
    first.flush()                         # the first save holds today's row, not committed

    def save_second():
        try:
            second_profile.weight = 90
            second.commit()
            outcome["second"] = "saved"
        except Exception as exc:          # pragma: no cover - the regression
            outcome["second"] = type(exc).__name__
            second.rollback()

    worker = threading.Thread(target=save_second)
    worker.start()
    worker.join(timeout=1.0)
    assert worker.is_alive(), "the second save should wait for the first, not race it"
    first.commit()
    worker.join(timeout=15)
    first.close()
    second.close()

    assert outcome == {"second": "saved"}
    rows = NutritionGoalHistory.query.filter_by(user_id=user.id).all()
    assert len(rows) == 1
    # 70 kg and 90 kg men, 180 cm, 30 y, moderate: BMR = 10*kg + 1125 - 150 + 5, x1.55;
    # the save that committed last (90 kg) is what the day ends with.
    assert rows[0].calories == round((10 * 90 + 980) * 1.55)
    assert UserProfile.query.filter_by(user_id=user.id).one().weight == 90


def test_two_simultaneous_saves_of_the_same_values_make_one_row(app, user):
    _fresh_user_with_profile(user)
    first, first_profile, second, second_profile = _two_sessions(user)
    errors = []

    first_profile.weight = 75
    first.flush()

    def save_second():
        try:
            second_profile.weight = 75
            second.commit()
        except Exception as exc:          # pragma: no cover
            errors.append(exc)
            second.rollback()

    worker = threading.Thread(target=save_second)
    worker.start()
    worker.join(timeout=1.0)
    first.commit()
    worker.join(timeout=15)
    first.close()
    second.close()
    assert errors == []
    assert NutritionGoalHistory.query.filter_by(user_id=user.id).count() == 1


def test_the_write_is_an_atomic_upsert_not_check_then_insert(app, user):
    """A row for today appears between the read and the write (another
    transaction committed it): the write must update it, not fail."""
    from sqlalchemy import create_engine

    _fresh_user_with_profile(user)
    other = create_engine(db.engine.url)
    state = {"done": False}

    def intrude(conn, cursor, statement, *args):
        if statement.lstrip().upper().startswith("INSERT INTO NUTRITION_GOAL_HISTORY") and not state["done"]:
            state["done"] = True
            with other.begin() as connection:
                connection.execute(db.text(
                    "INSERT INTO nutrition_goal_history (user_id, effective_from, calories, protein, fat, carbs, "
                    "fiber, created_at) VALUES (:u, :d, 1, 1, 1, 1, 1, now())"),
                    {"u": user.id, "d": clock.today()})

    event.listen(db.engine, "before_cursor_execute", intrude)
    try:
        profile = UserProfile.query.filter_by(user_id=user.id).one()
        profile.weight = 85
        db.session.commit()               # would raise IntegrityError with check-then-insert
    finally:
        event.remove(db.engine, "before_cursor_execute", intrude)
        other.dispose()

    assert state["done"]
    rows = NutritionGoalHistory.query.filter_by(user_id=user.id).all()
    assert len(rows) == 1 and rows[0].calories == round((10 * 85 + 980) * 1.55)


def test_repeated_saves_and_changes_keep_the_documented_semantics(app, user, monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: dt.datetime(2024, 8, 1, 9, 0, tzinfo=KYIV))
    add_profile(user)
    profile = UserProfile.query.filter_by(user_id=user.id).one()
    for _ in range(3):
        profile.weight = profile.weight           # no change
        db.session.commit()
    assert NutritionGoalHistory.query.count() == 1
    profile.weight = 72
    db.session.commit()
    profile.weight = 73
    db.session.commit()
    rows = NutritionGoalHistory.query.all()
    assert len(rows) == 1 and rows[0].calories == round((10 * 73 + 980) * 1.55)   # same day: updated in place
    monkeypatch.setattr(clock, "now", lambda: dt.datetime(2024, 8, 2, 9, 0, tzinfo=KYIV))
    profile.weight = 74
    db.session.commit()
    assert [r.effective_from for r in NutritionGoalHistory.query.order_by(NutritionGoalHistory.effective_from)] == [
        dt.date(2024, 8, 1), dt.date(2024, 8, 2)]
    db.session.rollback()
    profile = UserProfile.query.filter_by(user_id=user.id).one()
    profile.weight = 60
    db.session.flush()
    db.session.rollback()                         # a failed save leaves no row behind
    assert NutritionGoalHistory.query.count() == 2


# --- the history is calculated from the state that is saved (B1) ------------
#
# Hand arithmetic for the 80 kg / 180 cm / 30 y / male / moderate profile:
#   targets = (10*kg + 6.25*cm - 5*30 + 5) * 1.55, rounded
#   190 cm, 90 kg: (900 + 1187.5 - 145) * 1.55 = 3010.875 -> 3011
#   180 cm, 90 kg: (900 + 1125   - 145) * 1.55 = 2914
#   190 cm, 80 kg: (800 + 1187.5 - 145) * 1.55 = 2856
#   180 cm, 80 kg: 2759

def _history(user):
    return NutritionGoalHistory.query.filter_by(user_id=user.id).all()


def _save_in_thread(session, change):
    """Run ``change`` + commit on its own thread; returns (thread, outcome dict)."""
    outcome = {}

    def work():
        try:
            change()
            session.commit()
            outcome["result"] = "saved"
        except Exception as exc:          # pragma: no cover - a regression
            outcome["result"] = f"{type(exc).__name__}: {str(getattr(exc, 'orig', exc))[:80]}"
            session.rollback()

    thread = threading.Thread(target=work)
    thread.start()
    thread.join(timeout=1.0)
    return thread, outcome


def test_concurrent_changes_of_different_fields_give_one_consistent_state(app, user):
    """A changes the height, B the weight, at the same moment: the profile ends
    with both, and the history must describe exactly that - not B's stale height."""
    _fresh_user_with_profile(user)
    first, first_profile, second, second_profile = _two_sessions(user)      # both read 180 cm / 80 kg
    first_profile.height = 190
    first.flush()                                                           # holds the lock, not committed

    thread, outcome = _save_in_thread(second, lambda: setattr(second_profile, "weight", 90))
    assert thread.is_alive(), "the second save must wait for the first"
    first.commit()
    thread.join(timeout=15)
    first.close()
    second.close()

    assert outcome == {"result": "saved"}
    db.session.expire_all()
    profile = UserProfile.query.filter_by(user_id=user.id).one()
    assert (profile.height, profile.weight) == (190, 90)
    rows = _history(user)
    assert len(rows) == 1 and rows[0].calories == 3011                      # not 2914 (stale height)


def test_the_same_in_the_other_order(app, user):
    _fresh_user_with_profile(user)
    first, first_profile, second, second_profile = _two_sessions(user)
    first_profile.weight = 90
    first.flush()
    thread, outcome = _save_in_thread(second, lambda: setattr(second_profile, "height", 190))
    assert thread.is_alive()
    first.commit()
    thread.join(timeout=15)
    first.close()
    second.close()
    assert outcome == {"result": "saved"}
    db.session.expire_all()
    profile = UserProfile.query.filter_by(user_id=user.id).one()
    assert (profile.height, profile.weight) == (190, 90)
    rows = _history(user)
    assert len(rows) == 1 and rows[0].calories == 3011                      # not 2856 (stale weight)


def test_a_concurrent_save_that_makes_the_profile_incomplete_is_not_overwritten(app, user):
    """A clears the weight (no targets any more); B changes the height. The
    history must not get a row calculated with the weight A just removed."""
    _fresh_user_with_profile(user)
    db.session.execute(db.text("DELETE FROM nutrition_goal_history"))
    db.session.execute(db.text(
        "INSERT INTO nutrition_goal_history (user_id, effective_from, calories, protein, fat, carbs, fiber, created_at) "
        "VALUES (:u, :d, 2759, 128, 85.8, 368.6, 30, now())"), {"u": user.id, "d": clock.today()})
    db.session.commit()

    first, first_profile, second, second_profile = _two_sessions(user)
    first_profile.weight = None
    first.flush()
    thread, outcome = _save_in_thread(second, lambda: setattr(second_profile, "height", 190))
    assert thread.is_alive()
    first.commit()
    thread.join(timeout=15)
    first.close()
    second.close()

    assert outcome == {"result": "saved"}
    db.session.expire_all()
    profile = UserProfile.query.filter_by(user_id=user.id).one()
    assert profile.weight is None and profile.height == 190
    rows = _history(user)
    assert len(rows) == 1 and rows[0].calories == 2759                      # untouched: no valid state to record
    from backend.app.services.nutrition.goals_service import get_goals

    assert get_goals(user.id)["source"] != "profile"


def test_a_writer_that_already_holds_the_row_does_not_deadlock_with_another(app, user):
    """The earlier ordering problem: A had locked the row through a column the
    targets do not use and then asked for the advisory lock held by B."""
    _fresh_user_with_profile(user)
    first, first_profile, second, second_profile = _two_sessions(user)
    first_profile.training_location = "gym"
    first.flush()                                          # A: lock first, then the row
    thread, outcome = _save_in_thread(second, lambda: setattr(second_profile, "weight", 85))
    assert thread.is_alive()
    first_profile.weight = 70                              # A needs nothing it does not hold
    first.commit()
    thread.join(timeout=15)
    first.close()
    second.close()

    assert outcome == {"result": "saved"}                  # was: deadlock detected
    db.session.expire_all()
    profile = UserProfile.query.filter_by(user_id=user.id).one()
    assert (profile.weight, profile.training_location) == (85, "gym")
    rows = _history(user)
    assert len(rows) == 1 and rows[0].calories == round((10 * 85 + 980) * 1.55)


def test_a_rolled_back_save_releases_the_lock_and_leaves_no_trace(app, user):
    _fresh_user_with_profile(user)
    first, first_profile, second, second_profile = _two_sessions(user)
    first_profile.weight = 70
    first.flush()
    thread, outcome = _save_in_thread(second, lambda: setattr(second_profile, "weight", 90))
    assert thread.is_alive()
    first.rollback()                                       # the first save fails
    thread.join(timeout=15)
    first.close()
    second.close()
    assert outcome == {"result": "saved"}
    rows = _history(user)
    assert len(rows) == 1 and rows[0].calories == 2914     # only the save that committed


def test_the_lock_is_taken_before_any_write_of_the_profile_row(app, user):
    add_profile(user)
    seen = []

    def record(conn, cursor, statement, *args):
        text_ = statement.lstrip().upper()
        if "PG_ADVISORY_XACT_LOCK" in text_:
            seen.append("lock")
        elif text_.startswith("UPDATE USER_PROFILES"):
            seen.append("profile-update")

    event.listen(db.engine, "before_cursor_execute", record)
    try:
        profile = UserProfile.query.filter_by(user_id=user.id).one()
        profile.training_location = "gym"                  # not an input of the targets
        db.session.commit()
        assert seen == ["lock", "profile-update"]
        seen.clear()
        profile.weight = 81
        db.session.commit()
        assert seen[:1] == ["lock"] and seen.count("lock") == 1 and "profile-update" in seen
        seen.clear()
        db.session.add(Meal(user_id=user.id, date=dt.date.today(), name="x", category="lunch"))
        db.session.commit()
        assert "lock" not in seen                          # no profile write, no lock
    finally:
        event.remove(db.engine, "before_cursor_execute", record)


def test_goal_inputs_are_read_fresh_but_pending_changes_win(app, user):
    from backend.app.models.nutrition.goal_history import current_goal_inputs

    add_profile(user)
    session, profile = _two_sessions(user)[:2]              # loaded: 180 cm / 80 kg
    db.session.execute(db.text("UPDATE user_profiles SET height = 195, age = 41 WHERE user_id = :u"), {"u": user.id})
    db.session.commit()                                    # committed behind the loaded object's back
    profile.weight = 77                                    # this transaction's own change
    inputs = current_goal_inputs(session, profile)
    assert inputs == {"weight": 77, "height": 195, "age": 41, "gender": "male",
                      "activity": "moderate", "goal": "maintenance"}
    session.close()


def test_the_fresh_read_relies_on_read_committed(app):
    with db.engine.connect() as connection:
        assert connection.execute(db.text("SHOW transaction_isolation")).scalar() == "read committed"
