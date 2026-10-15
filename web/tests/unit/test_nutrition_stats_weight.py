"""Calorie balance, statistics windows, weight trend and BMI, input validation."""
import datetime as dt
from zoneinfo import ZoneInfo

import pytest

from backend.app.extensions import db
from backend.app.models import Meal, MealItem, Product, UserProfile, UserWeight
from backend.app.services.nutrition import calculation_service as calc
from backend.app.services.nutrition import stats_service as stats
from backend.app.services.nutrition.day_service import (
    CALORIE_TOLERANCE,
    calculate_percent,
    calorie_status,
    get_daily_nutrition_data,
)
from backend.app.services.nutrition.item_service import add_item_service
from backend.app.services.nutrition.weight_service import (
    bmi_category,
    calculate_bmi,
    get_weight_data,
    update_user_weight,
)
from backend.app.utils import clock
from backend.app.utils.validation import PROFILE_RANGES

KYIV = ZoneInfo("Europe/Kyiv")
TODAY = dt.date(2024, 5, 10)


@pytest.fixture
def fixed_today(monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: dt.datetime(2024, 5, 10, 12, 0, tzinfo=KYIV))
    return TODAY


def add_profile(user, **values):
    base = dict(training_location="home", weight=80, height=180, age=30, gender="male",
                activity="moderate", goal="maintenance")
    base.update(values)
    db.session.add(UserProfile(user_id=user.id, **base))
    db.session.commit()


def eat(user, day, kcal, items=1):
    meal = Meal(user_id=user.id, date=day, name="x", category="lunch", total_calories=kcal)
    db.session.add(meal)
    db.session.flush()
    for _ in range(items):
        db.session.add(MealItem(meal_id=meal.id, name="x", calories=kcal // items, protein=0, fat=0, carbs=0))
    db.session.commit()


# --- calorie status -------------------------------------------------------

@pytest.mark.parametrize(
    "consumed, goal, entries, status",
    [
        (1799, 2000, True, "under"),       # -10.05%
        (1800, 2000, True, "normal"),      # exactly -10%
        (2000, 2000, True, "normal"),
        (2200, 2000, True, "normal"),      # exactly +10%
        (2201, 2000, True, "over"),
        (0, 2000, True, "under"),          # entries logged, all without energy
        (0, 2000, False, "no_data"),       # nothing logged
        (1500, 0, True, "unavailable"),    # a zero target is no target
        (1500, None, True, "unavailable"),
        (1500, -5, True, "unavailable"),
        (0, 0, False, "unavailable"),
        (5000, 0, True, "unavailable"),    # never "over" for lack of a target
    ],
)
def test_calorie_status(consumed, goal, entries, status):
    assert calorie_status(consumed, goal, entries) == status


def test_the_tolerance_is_ten_percent_everywhere():
    assert CALORIE_TOLERANCE == 0.10


@pytest.mark.parametrize("value, goal, expected", [(50, 200, 25.0), (0, 200, 0.0), (300, 200, 150.0),
                                                   (50, 0, None), (50, None, None), (50, -1, None)])
def test_percent_of_a_target(value, goal, expected):
    assert calculate_percent(value, goal) == expected


def test_a_day_without_targets_is_not_over(app, user, fixed_today):
    eat(user, TODAY, 3000)
    day = get_daily_nutrition_data(user.id)
    assert day["balance_status"] == "unavailable" and day["goals_available"] is False
    assert day["kcal_balance"] is None and day["kcal_remaining"] is None
    assert day["kcal_percent"] is None and day["protein_percent"] is None
    assert day["kcal_goal"] == 0


def test_a_day_with_targets_has_consistent_numbers(app, user, fixed_today):
    add_profile(user)          # target 2759
    eat(user, TODAY, 2000)
    day = get_daily_nutrition_data(user.id)
    assert day["kcal"] == 2000 and day["kcal_goal"] == 2759
    assert day["kcal_balance"] == 2000 - 2759
    assert day["kcal_remaining"] == 759
    assert day["kcal_percent"] == pytest.approx(2000 / 2759 * 100, abs=0.05)
    assert day["balance_status"] == "under" and day["goals_available"] is True
    assert day["water_goal"] == 3.09 and day["water_percent"] == 0.0


def test_an_empty_day_with_targets(app, user, fixed_today):
    add_profile(user)
    day = get_daily_nutrition_data(user.id)
    assert day["balance_status"] == "no_data"
    assert day["kcal"] == 0 and day["kcal_remaining"] == 2759
    assert day["quality"]["score"] is None


def test_exceeding_the_target_leaves_nothing_remaining(app, user, fixed_today):
    add_profile(user)
    eat(user, TODAY, 3500)
    day = get_daily_nutrition_data(user.id)
    assert day["balance_status"] == "over" and day["kcal_remaining"] == 0 and day["kcal_balance"] == 741


# --- statistics windows ---------------------------------------------------

def test_the_chart_marks_unlogged_days_unknown_not_zero(app, user, fixed_today):
    eat(user, TODAY - dt.timedelta(days=1), 2000)
    eat(user, TODAY - dt.timedelta(days=3), 1800)
    data = stats.get_stats(user.id, 5)
    assert data["kcal"]["labels"] == ["06.05", "07.05", "08.05", "09.05", "10.05"]
    assert data["kcal"]["values"] == [None, 1800, None, 2000, None]
    assert data["kcal"]["logged"] == [False, True, False, True, False]


def test_average_counts_logged_days_only(app, user, fixed_today):
    for ago, kcal in ((1, 2000), (2, 1800), (4, 2200)):
        eat(user, TODAY - dt.timedelta(days=ago), kcal)
    data = stats.get_stats(user.id, 7)        # seven days, three of them logged
    assert data["avg_kcal"] == 2000 and data["avg_kcal_days"] == 3   # not 6000/7


def test_today_is_left_out_of_the_average_while_it_is_still_in_progress(app, user, fixed_today):
    eat(user, TODAY - dt.timedelta(days=1), 2000)
    eat(user, TODAY, 400)                      # breakfast only so far
    data = stats.get_stats(user.id, 7)
    assert data["avg_kcal"] == 2000 and data["avg_kcal_days"] == 1
    assert data["kcal"]["values"][-1] == 400   # still shown on the chart


def test_today_alone_is_used_when_it_is_all_there_is(app, user, fixed_today):
    eat(user, TODAY, 900)
    assert stats.get_stats(user.id, 7)["avg_kcal"] == 900


def test_no_logged_days_means_no_average(app, user, fixed_today):
    data = stats.get_stats(user.id, 7)
    assert data["avg_kcal"] is None and data["avg_kcal_days"] == 0
    assert data["goal_kcal"] is None and data["current_weight"] is None


def test_a_logged_day_without_energy_is_not_an_intake(app, user, fixed_today):
    eat(user, TODAY - dt.timedelta(days=1), 0)          # only tea
    eat(user, TODAY - dt.timedelta(days=2), 1600)
    data = stats.get_stats(user.id, 7)
    assert data["kcal"]["logged"][-2] is True and data["kcal"]["values"][-2] == 0   # genuinely zero
    assert data["avg_kcal"] == 1600 and data["avg_kcal_days"] == 1


def test_the_weight_series_respects_the_requested_window(app, user, fixed_today):
    add_profile(user)
    for ago, kg in ((400, 90.0), (40, 82.0), (10, 81.0), (6, 80.5), (0, 80.0)):
        db.session.add(UserWeight(user_id=user.id, date=TODAY - dt.timedelta(days=ago), weight=kg))
    db.session.commit()

    week = stats.get_stats(user.id, 7)
    assert week["weight"]["values"] == [80.5, 80.0]
    assert week["weight"]["labels"] == ["04.05", "10.05"]
    month = stats.get_stats(user.id, 30)
    assert month["weight"]["values"] == [81.0, 80.5, 80.0]
    assert len(stats.get_stats(user.id, 365)["weight"]["values"]) == 4      # the 400-day-old one is out
    assert week["current_weight"] == 80.0


def test_the_current_weight_is_the_latest_even_outside_the_window(app, user, fixed_today):
    db.session.add(UserWeight(user_id=user.id, date=TODAY - dt.timedelta(days=20), weight=77.5))
    db.session.commit()
    data = stats.get_stats(user.id, 7)
    assert data["weight"]["values"] == [] and data["current_weight"] == 77.5


def test_the_stats_endpoint_clamps_the_window(app, user, client, fixed_today):
    client.post("/auth/login", data={"email": user.email, "password": "password123"})
    assert len(client.get("/api/nutrition/stats?days=0").get_json()["kcal"]["labels"]) == 1
    assert len(client.get("/api/nutrition/stats?days=9999").get_json()["kcal"]["labels"]) == 365
    assert len(client.get("/api/nutrition/stats?days=abc").get_json()["kcal"]["labels"]) == 7


# --- weight trend ----------------------------------------------------------

def series(*pairs):
    start = dt.date(2024, 4, 1)
    return [(start + dt.timedelta(days=d), kg) for d, kg in pairs]


def daily(kgs, start=dt.date(2024, 4, 1)):
    return [(start + dt.timedelta(days=i), kg) for i, kg in enumerate(kgs)]


def test_an_increasing_series():
    kgs = [70 + 0.5 * i / 7 for i in range(29)]        # +0.5 kg a week for four weeks
    result = stats.weight_trend(daily(kgs))
    assert result["direction"] == "increasing"
    assert result["kg_per_week"] == pytest.approx(0.5, abs=0.01)
    assert result["change_kg"] == pytest.approx(2.0, abs=0.02)
    assert result["span_days"] == 28 and result["measurements"] == 29


def test_a_decreasing_series():
    kgs = [90 - 0.3 * i / 7 for i in range(22)]
    result = stats.weight_trend(daily(kgs))
    assert result["direction"] == "decreasing" and result["kg_per_week"] == pytest.approx(-0.3, abs=0.01)


def test_ordinary_daily_fluctuation_is_stable():
    noise = [0.4, -0.3, 0.2, -0.5, 0.1, 0.45, -0.2, -0.4, 0.3, 0.0, -0.35, 0.25, 0.5, -0.45, 0.15, -0.1]
    result = stats.weight_trend(daily([75 + n for n in noise]))
    assert result["direction"] == "stable"


def test_one_wrong_weighing_does_not_make_a_trend():
    kgs = [75.0] * 21
    kgs[10] = 83.0            # a typo or a heavy meal
    kgs[3] = 66.0
    assert stats.weight_trend(daily(kgs))["direction"] == "stable"


def test_irregular_measurements_are_judged_by_their_dates():
    # +1.2 kg over 24 days, weighed on uneven days
    points = series((0, 80.0), (3, 80.1), (11, 80.5), (12, 80.6), (20, 81.0), (24, 81.2))
    result = stats.weight_trend(points)
    assert result["direction"] == "increasing"
    assert result["kg_per_week"] == pytest.approx(0.35, abs=0.03)


@pytest.mark.parametrize(
    "points",
    [
        [],
        series((0, 80.0)),
        series((0, 80.0), (14, 79.0)),                       # two weighings are not a trend
        series((0, 80.0), (2, 80.5), (4, 81.0)),             # three, but a few days only
        series((0, 80.0), (3, 80.0), (6, 81.0)),             # six days: under a week
    ],
)
def test_too_little_data_is_reported_as_such(points):
    assert stats.weight_trend(points)["direction"] == "insufficient_data"


def test_trend_thresholds():
    # two weeks, +0.5 kg: exactly the threshold -> a change
    assert stats.weight_trend(series((0, 80.0), (7, 80.25), (14, 80.5)))["direction"] == "increasing"
    # +0.49 kg: not
    assert stats.weight_trend(series((0, 80.0), (7, 80.245), (14, 80.49)))["direction"] == "stable"
    # a long slow drift of 0.05 kg a week stays stable although 1 kg in total
    slow = daily([80 - 0.05 * i / 7 for i in range(141)])
    assert stats.weight_trend(slow)["direction"] == "stable"


def test_implausible_values_are_ignored_by_the_trend():
    points = series((0, 80.0), (3, 0.0), (7, 80.0), (10, 5000), (14, 80.0))
    assert stats.weight_trend(points)["direction"] == "stable"
    assert stats.weight_trend(points)["measurements"] == 3


def test_the_stats_report_the_trend_as_a_code_not_a_translated_word(app, user, fixed_today):
    for ago in range(0, 28, 2):
        db.session.add(UserWeight(user_id=user.id, date=TODAY - dt.timedelta(days=ago),
                                  weight=78 + 0.07 * ago))   # lighter now: 0.49 kg a week
    db.session.commit()
    data = stats.get_stats(user.id, 7)
    assert data["weight_trend"] == "decreasing"
    assert data["weight_trend_detail"]["kg_per_week"] == pytest.approx(-0.49, abs=0.02)
    assert data["weight_trend"] != "Стабільно"
    # The week shown has fewer points than the trend needs; the trend still looks back two weeks.
    assert len(data["weight"]["values"]) == 4


def test_a_short_window_still_gets_a_two_week_trend(app, user, fixed_today):
    db.session.add_all([UserWeight(user_id=user.id, date=TODAY - dt.timedelta(days=d), weight=kg)
                        for d, kg in ((13, 82.0), (7, 81.0), (0, 80.0))])
    db.session.commit()
    assert stats.get_stats(user.id, 3)["weight_trend"] == "decreasing"
    assert stats.get_stats(user.id, 365)["weight_trend"] == "decreasing"


def test_no_weighings_no_trend(app, user, fixed_today):
    assert stats.get_stats(user.id, 7)["weight_trend"] == "insufficient_data"


# --- BMI -------------------------------------------------------------------

@pytest.mark.parametrize(
    "bmi, age, category",
    [(18.4, 30, "underweight"), (18.5, 30, "normal"), (24.9, 30, "normal"), (25.0, 30, "overweight"),
     (29.9, 30, "overweight"), (30.0, 30, "obese"), (41.2, 70, "obese"),
     (22.0, 17, None), (22.0, 10, None), (22.0, None, None), (None, 30, None), (22.0, 18, "normal")],
)
def test_bmi_categories_are_adult_only(bmi, age, category):
    assert bmi_category(bmi, age) == category


@pytest.mark.parametrize(
    "weight, height, bmi",
    [(80, 180, 24.7), (60, 165, 22.0), (100, 170, 34.6), (None, 180, None), (80, None, None),
     (80, 0, None), (0, 180, None), (80, 40, None), (80, 300, None), (500, 180, None), ("x", 180, None)],
)
def test_bmi_value(weight, height, bmi):
    assert calculate_bmi(weight, height) == bmi


def test_weight_endpoint_data(app, user, fixed_today):
    add_profile(user, weight=80, height=180, age=30)
    data = get_weight_data(user.id)
    assert (data["weight"], data["bmi"], data["bmi_category"], data["bmi_classified"]) == (80, 24.7, "normal", True)

    UserProfile.query.filter_by(user_id=user.id).first().age = 16
    db.session.commit()
    teen = get_weight_data(user.id)
    assert teen["bmi"] == 24.7 and teen["bmi_category"] is None and teen["bmi_classified"] is False


def test_weight_limits_are_the_profile_limits(app, user, client, fixed_today):
    low, high, _ = PROFILE_RANGES["weight"]
    assert (low, high) == (20.0, 400.0)
    client.post("/auth/login", data={"email": user.email, "password": "password123"})
    for weight, ok in ((19.9, False), (20, True), (400, True), (400.1, False), ("abc", False), (None, False)):
        response = client.post("/api/nutrition/weight", json={"weight": weight})
        assert (response.status_code == 200) == ok, weight
        if not ok:
            assert response.get_json()["code"] == "invalid_weight"


def test_a_weighing_belongs_to_the_application_day(app, user, monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: dt.datetime(2024, 5, 1, 23, 50, tzinfo=KYIV))
    entry = update_user_weight(user, 75)
    assert entry.date == dt.date(2024, 5, 1)
    monkeypatch.setattr(clock, "now", lambda: dt.datetime(2024, 5, 2, 0, 5, tzinfo=KYIV))
    assert update_user_weight(user, 74.5).date == dt.date(2024, 5, 2)
    assert UserWeight.query.count() == 2


# --- entry validation -----------------------------------------------------

def make_product(**values):
    base = dict(source="system", category="other", kcal_per_100g=100, protein_per_100g=5, fat_per_100g=2,
                carbs_per_100g=15, default_unit="g", grams_per_unit=1, liquid_ml_per_100g=0)
    base.update(values)
    product = Product(**base)
    db.session.add(product)
    db.session.commit()
    return product


@pytest.mark.parametrize(
    "unit, per_unit, amount, ok",
    [
        ("g", 1, 5000, True),
        ("g", 1, 5000.01, False),
        ("pcs", 50, 100, True),          # 5 kg
        ("pcs", 50, 100.5, False),       # over the pieces limit
        ("pcs", 51, 100, False),         # 5.1 kg: passes the pieces limit, not the mass limit
        ("pcs", 500, 100, False),        # 50 kg
        ("pcs", 500, 10, True),
        ("ml", 1.0, 5000, True),
        ("ml", 1.4, 5000, False),        # 7 kg of syrup in one entry
        ("ml", 1.4, 3500, True),
    ],
)
def test_a_single_entry_cannot_weigh_more_than_five_kilograms(unit, per_unit, amount, ok):
    product = SimpleNamespace_product(unit, per_unit)
    if ok:
        result = calc.calculate_product_nutrition(product, amount, unit)
        assert result.grams <= 5000.0
    else:
        with pytest.raises(calc.NutritionValidationError):
            calc.calculate_product_nutrition(product, amount, unit)


def SimpleNamespace_product(unit, per_unit):
    from types import SimpleNamespace

    return SimpleNamespace(kcal_per_100g=100, protein_per_100g=5, fat_per_100g=2, carbs_per_100g=15,
                           fiber_per_100g=None, sugar_per_100g=None, saturated_fat_per_100g=None,
                           salt_per_100g=None, liquid_ml_per_100g=0, default_unit=unit, grams_per_unit=per_unit)


@pytest.mark.parametrize("amount", [0, -1, float("nan"), float("inf"), "abc", None, "", 1e12])
def test_invalid_amounts_are_rejected(amount):
    with pytest.raises(calc.NutritionValidationError):
        calc.calculate_product_nutrition(SimpleNamespace_product("g", 1), amount, "g")


def test_unknown_nutrients_are_never_turned_into_zeros():
    product = SimpleNamespace_product("g", 1)
    result = calc.calculate_product_nutrition(product, 200, "g")
    assert result.fiber is None and result.sugar is None and result.saturated_fat is None and result.salt is None
    zero = SimpleNamespace_product("g", 1)
    zero.fiber_per_100g = 0.0
    assert calc.calculate_product_nutrition(zero, 200, "g").fiber == 0.0


def test_conversions_and_rounding():
    product = SimpleNamespace_product("pcs", 60)        # one piece = 60 g
    product.fiber_per_100g = 2.5
    result = calc.calculate_product_nutrition(product, 2.5, "pcs")   # 150 g
    assert result.grams == 150 and result.calories == 150 and result.fiber == 3.75
    assert result.protein == 7.5 and result.fat == 3.0 and result.carbs == 22.5
    # 1 ml of a 1.03 g/ml drink with 87.5 ml of fluid per 100 g counts as 1 ml of fluid
    drink = SimpleNamespace_product("ml", 1.03)
    drink.liquid_ml_per_100g = 87.5
    assert calc.calculate_product_nutrition(drink, 250, "ml").liquid_ml == 250
    assert calc.calculate_product_nutrition(drink, 250, "ml").grams == 257.5


def test_logging_an_oversized_portion_through_the_service(app, user):
    product = make_product(default_unit="pcs", grams_per_unit=500)
    meal = Meal(user_id=user.id, date=dt.date.today(), name="x", category="lunch")
    db.session.add(meal)
    db.session.commit()
    with pytest.raises(calc.NutritionValidationError):
        add_item_service(user.id, {"meal_id": meal.id, "product_id": product.id, "amount": 20, "unit": "pcs"})
    assert MealItem.query.count() == 0
    ok = add_item_service(user.id, {"meal_id": meal.id, "product_id": product.id, "amount": 10, "unit": "pcs"})
    assert ok.weight == 5000
