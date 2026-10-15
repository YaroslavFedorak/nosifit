"""Nutrition recommendations: every rule, its boundaries and its guard rails.

The profile is the 80 kg, 180 cm, 30 y man of the goal tests, so the targets
are known by hand: 2759 kcal, 128 g protein, 85.8 g fat, 368.6 g carbs,
30 g fibre, and 3.09 L of fluid (moderate activity).
"""
import datetime as dt
from zoneinfo import ZoneInfo

import pytest

from backend.app.extensions import db
from backend.app.models import Meal, MealItem, UserProfile
from backend.app.services.nutrition import recommendation_service as rec
from backend.app.services.nutrition.water_service import add_water_service
from backend.app.utils import clock

KYIV = ZoneInfo("Europe/Kyiv")
DAY = dt.date(2024, 5, 10)


def at(hour, minute=0, tz=KYIV):
    return dt.datetime(2024, 5, 10, hour, minute, tzinfo=tz)


LATE = at(22)
EVENING = at(19)
AFTERNOON = at(14)
MORNING = at(9)


@pytest.fixture
def profile(app, user, monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: LATE)
    row = UserProfile(user_id=user.id, training_location="home", weight=80, height=180, age=30,
                      gender="male", activity="moderate", goal="maintenance")
    db.session.add(row)
    db.session.commit()
    return row


def item(name, category, kcal, protein=0.0, fat=0.0, carbs=0.0, fiber=0.0, sugar=0.0,
         saturated_fat=0.0, salt=0.0, grams=100.0, liquid_ml=0.0):
    return dict(name=name, category=category, calories=kcal, protein=protein, fat=fat, carbs=carbs,
                fiber=fiber, sugar=sugar, saturated_fat=saturated_fat, salt=salt, weight=grams,
                liquid_ml=liquid_ml)


def balanced():
    """About 2886 kcal of mostly whole food, meeting every target."""
    return [
        item("oats", "grains", 555, 20, 10, 100, fiber=15, sugar=1.5, saturated_fat=1.8, salt=0.03, grams=150),
        item("banana", "fruits", 267, 3, 1, 70, fiber=8, sugar=36, saturated_fat=0.3, salt=0.0, grams=300),
        item("chicken", "poultry", 550, 115, 8, 0, fiber=0, sugar=0, saturated_fat=2.2, salt=0.55, grams=500),
        item("rice", "grains", 780, 16, 2, 170, fiber=2.4, sugar=0.6, saturated_fat=0.6, salt=0.1, grams=600),
        item("broccoli", "vegetables", 136, 11, 1.6, 20, fiber=10.4, sugar=6.8, saturated_fat=0.2, salt=0.3, grams=400),
        item("olive oil", "oils", 354, 0, 40, 0, fiber=0, sugar=0, saturated_fat=5.6, salt=0.0, grams=40),
        item("yogurt", "dairy", 244, 20, 8, 18.8, fiber=0, sugar=18.8, saturated_fat=5.2, salt=0.44, grams=400),
    ]


def log(user, items, day=DAY):
    meal = Meal(user_id=user.id, date=day, name="Обід", category="Обід")
    db.session.add(meal)
    db.session.flush()
    for values in items:
        values = dict(values)
        category = values.pop("category")
        db.session.add(MealItem(meal_id=meal.id, basis={"category": category}, **values))
    db.session.flush()
    meal.total_calories = sum(i["calories"] for i in items)
    db.session.commit()
    return meal


def recommend(user, now=LATE):
    return rec.get_nutrition_recommendations(user.id, now=now)


def of_type(result, kind):
    return [r for r in result["recommendations"] if r["type"] == kind]


def types(result):
    return [r["type"] for r in result["recommendations"]]


def with_calories(kcal, filler="oils"):
    """Chicken, a banana and a filler adding up to ``kcal``.

    The filler is an oil (neutral) unless another category is given.
    """
    base = [
        item("chicken", "poultry", 400, 100, 4, 0, fiber=0, sugar=0, saturated_fat=1, salt=0.5, grams=400),
        item("banana", "fruits", 100, 0, 0, 25, fiber=30, sugar=20, saturated_fat=0, salt=0.0, grams=100),
    ]
    filler_kcal = max(kcal - 500, 0)
    return base + [item("filler", filler, filler_kcal, 0, filler_kcal / 9, 0, fiber=0, sugar=0, saturated_fat=0, salt=0.0, grams=100)]


# --- the quiet day --------------------------------------------------------

def test_a_balanced_day_gets_no_advice(app, user, profile):
    log(user, balanced())
    add_water_service(user.id, 3.0, DAY)
    result = recommend(user)
    assert result["recommendations"] == []
    summary = result["summary"]
    assert summary["quality_score"] == 100 and summary["day_progress"] == "late"
    assert summary["calories_goal"] == 2759 and summary["goals_available"] is True
    assert summary["fiber"] == 35.8 and summary["fiber_complete"] is True and summary["fiber_goal"] == 30
    assert summary["water"] == 3.0 and summary["water_goal"] == 3.09


def test_an_empty_day_asks_for_the_first_meal_and_nothing_else(app, user, profile):
    result = recommend(user)
    assert types(result) == ["balance"]
    assert result["recommendations"][0]["message_key"] == "recommendations.items.empty.message"
    assert result["summary"]["quality_score"] is None
    assert result["summary"]["fiber"] is None   # unknown, not 0


def test_without_targets_there_is_no_target_based_advice(app, user):
    # No profile at all.
    log(user, with_calories(900))
    result = recommend(user)
    assert types(result) == ["profile"]
    assert result["summary"]["goals_available"] is False and result["summary"]["calories_goal"] == 0
    assert result["summary"]["water_goal"] is None
    # ...but a limit that does not need a target still applies.
    salty = with_calories(900)
    salty[0]["salt"] = 5.5
    db.session.query(MealItem).delete()
    db.session.query(Meal).delete()
    db.session.commit()
    log(user, salty)
    assert set(types(recommend(user))) == {"profile", "salt"}


# --- phases of the day ----------------------------------------------------

@pytest.mark.parametrize(
    "moment, phase",
    [(at(0), "morning"), (at(11, 59), "morning"), (at(12), "day"), (at(17, 59), "day"),
     (at(18), "evening"), (at(20, 59), "evening"), (at(21), "late"), (at(23, 59), "late")],
)
def test_phase_boundaries(moment, phase):
    assert rec._get_day_progress(moment) == phase


def test_the_phase_is_read_in_the_application_zone_not_the_server_s(app, user, profile):
    log(user, balanced())
    # 17:30 UTC is 20:30 in Kyiv (UTC+3 in May): evening, not "day".
    assert recommend(user, now=dt.datetime(2024, 5, 10, 17, 30, tzinfo=dt.timezone.utc))["summary"]["day_progress"] == "evening"
    # 15:30 UTC is 18:30 in Kyiv.
    assert recommend(user, now=dt.datetime(2024, 5, 10, 15, 30, tzinfo=dt.timezone.utc))["summary"]["day_progress"] == "evening"
    # 14:30 UTC is 17:30 in Kyiv.
    assert recommend(user, now=dt.datetime(2024, 5, 10, 14, 30, tzinfo=dt.timezone.utc))["summary"]["day_progress"] == "day"


def test_the_day_of_the_advice_is_the_application_day(app, user, profile):
    log(user, balanced())
    # 23:30 UTC on the 9th is already the 10th in Kyiv: that day's food counts.
    late_utc = dt.datetime(2024, 5, 9, 23, 30, tzinfo=dt.timezone.utc)
    assert recommend(user, now=late_utc)["summary"]["calories"] == 2886
    # 20:30 UTC on the 10th is the 11th in Kyiv: nothing logged yet.
    assert recommend(user, now=dt.datetime(2024, 5, 10, 21, 30, tzinfo=dt.timezone.utc))["summary"]["calories"] == 0


def test_end_of_day_rules_wait_for_the_evening(app, user, profile):
    log(user, with_calories(700))
    assert not of_type(recommend(user, MORNING), "calories")
    assert not of_type(recommend(user, MORNING), "protein")
    assert not of_type(recommend(user, AFTERNOON), "calories")
    assert of_type(recommend(user, EVENING), "calories")
    assert of_type(recommend(user, LATE), "calories")


def test_protein_pacing_is_an_afternoon_hint(app, user, profile):
    # Target 128 g: 40% remaining = 51.2 g.
    low = with_calories(1500)
    low[0]["protein"] = 76.7        # remaining 51.3 g
    log(user, low)
    assert of_type(recommend(user, AFTERNOON), "protein_progress")
    assert not of_type(recommend(user, MORNING), "protein_progress")
    assert not of_type(recommend(user, EVENING), "protein_progress")

    db.session.query(MealItem).delete()
    db.session.query(Meal).delete()
    db.session.commit()
    enough = with_calories(1500)
    enough[0]["protein"] = 76.9     # remaining 51.1 g: not more than 40%
    log(user, enough)
    assert not of_type(recommend(user, AFTERNOON), "protein_progress")


# --- calories -------------------------------------------------------------

@pytest.mark.parametrize(
    "kcal, kind",
    [
        (1931, "calories.low"),        # 69.99% of 2759
        (1932, "calories.remaining"),  # 70.0%
        (2483, "calories.remaining"),  # 89.99%
        (2484, None),                  # 90.0%
        (3034, None),                  # 109.97%
        (3035, "calories.excess"),     # 110.0% is the edge; 3035 is 110.003%
        (4000, "calories.excess"),
    ],
)
def test_calorie_thresholds(app, user, profile, kcal, kind):
    log(user, with_calories(kcal))
    found = of_type(recommend(user), "calories")
    if kind is None:
        assert found == []
    else:
        assert [r["message_key"] for r in found] == [f"recommendations.items.{kind}.message"]


def test_under_the_target_is_the_plan_on_a_fat_loss_goal(app, user, profile):
    profile.goal = "fat_loss"
    db.session.commit()
    # fat loss target = 2759 * 0.85 = 2345; 80% of it is under 90% but not under 70%
    log(user, with_calories(1876))
    assert of_type(recommend(user), "calories") == []
    # Far under is still worth saying.
    db.session.query(MealItem).delete()
    db.session.query(Meal).delete()
    db.session.commit()
    log(user, with_calories(1200))
    assert [r["message_key"] for r in of_type(recommend(user), "calories")] == [
        "recommendations.items.calories.low.message"
    ]


def test_calorie_advice_carries_the_numbers(app, user, profile):
    log(user, with_calories(3300))
    (excess,) = of_type(recommend(user), "calories")
    assert excess["params"] == {"value": 3300 - 2759}


# --- protein, and the macros that are not advised on ----------------------

@pytest.mark.parametrize("protein, flagged", [(102.3, True), (102.4, False), (50, True), (128, False)])
def test_protein_shortfall_boundary(app, user, profile, protein, flagged):
    day = with_calories(2759)
    day[0]["protein"] = protein       # 80% of 128 g = 102.4 g
    log(user, day)
    found = of_type(recommend(user), "protein")
    assert bool(found) == flagged
    if flagged:
        assert found[0]["params"] == {"value": round(128 - protein), "macro": "protein"}


def test_protein_shortfall_is_urgent_only_late(app, user, profile):
    day = with_calories(2759)
    day[0]["protein"] = 40
    log(user, day)
    assert of_type(recommend(user, EVENING), "protein")[0]["priority"] == "medium"
    assert of_type(recommend(user, LATE), "protein")[0]["priority"] == "high"


def test_fat_and_carbohydrate_shortfalls_are_not_advised(app, user, profile):
    # Their targets are the energy left after protein, not requirements of their own.
    day = with_calories(2759)
    day[0].update(fat=0, carbs=0)
    log(user, day)
    assert not {"fat", "carbs"} & set(types(recommend(user)))


def test_macro_split_advice_only_for_a_calorie_neutral_day_without_a_protein_flag(app, user, profile):
    fatty = [
        item("chicken", "poultry", 560, 128, 0, 0, fiber=0, sugar=0, saturated_fat=0.5, salt=0.5, grams=400),
        item("oil", "oils", 2200, 0, 244, 0, fiber=0, sugar=0, saturated_fat=1, salt=0.0, grams=250),
        item("banana", "fruits", 0, 0, 0, 0, fiber=0, sugar=0, saturated_fat=0, salt=0.0, grams=100),
    ]   # 2760 kcal, 128 g protein, 244 g fat: the fat share is far above the target's
    log(user, fatty)
    found = of_type(recommend(user), "macro_balance")
    # Fat is 80% of the energy against 28% planned; carbohydrate is 0% against 53%,
    # the larger gap, so that is the one named.
    assert len(found) == 1 and found[0]["params"] == {"macro": "carbs", "direction": "lower"}

    db.session.query(MealItem).delete()
    db.session.query(Meal).delete()
    db.session.commit()
    low_protein = [dict(i) for i in fatty]
    low_protein[0].update(protein=20, calories=80)
    low_protein[1]["calories"] = 2680
    log(user, low_protein)
    result = recommend(user)
    assert of_type(result, "protein") and not of_type(result, "macro_balance")


# --- salt, fibre, sugar, saturated fat, water -----------------------------

@pytest.mark.parametrize("salt, flagged", [(4.9, False), (5.0, False), (5.1, True), (12, True)])
def test_salt_limit_applies_all_day(app, user, profile, salt, flagged):
    day = with_calories(900)
    day[0]["salt"] = salt
    log(user, day)
    for moment in (MORNING, AFTERNOON, LATE):
        found = of_type(recommend(user, moment), "salt")
        assert bool(found) == flagged
    if flagged:
        assert found[0]["params"] == {"value": round(salt, 1), "limit": 5.0}


def test_unknown_salt_is_neither_a_problem_nor_proof_of_none(app, user, profile):
    day = with_calories(900)
    for entry in day:
        entry["salt"] = None
    log(user, day)
    assert not of_type(recommend(user), "salt")
    # The known part alone already above the limit is enough to say so.
    db.session.query(MealItem).delete()
    db.session.query(Meal).delete()
    db.session.commit()
    partly = with_calories(900)
    partly[0]["salt"] = 5.6
    partly[1]["salt"] = None
    log(user, partly)
    assert of_type(recommend(user), "salt")


def test_fibre_advice_needs_known_fibre_that_is_short(app, user, profile):
    def day(fiber):
        entries = with_calories(2759)
        for entry in entries:
            entry["fiber"] = fiber
        entries[0]["fiber"] = fiber
        return entries

    # 80% of 30 g = 24 g
    short = day(0.0)
    short[1]["fiber"] = 23.9
    log(user, short)
    found = of_type(recommend(user), "fiber")
    assert len(found) == 1 and found[0]["params"] == {"value": 6}

    db.session.query(MealItem).delete()
    db.session.query(Meal).delete()
    db.session.commit()
    enough = day(0.0)
    enough[1]["fiber"] = 24.0
    log(user, enough)
    assert not of_type(recommend(user), "fiber")


def test_unknown_fibre_gives_no_fibre_advice_and_no_false_low_quality(app, user, profile):
    unknown = with_calories(2759, filler="poultry")
    for entry in unknown:
        entry["fiber"] = None
    log(user, unknown)
    result = recommend(user)
    assert not of_type(result, "fiber") and not of_type(result, "quality")
    assert result["summary"]["fiber"] is None and result["summary"]["fiber_complete"] is False
    assert result["summary"]["quality_score"] is not None


def test_fibre_reaches_the_summary_and_the_quality_score(app, user, profile):
    log(user, balanced())
    summary = recommend(user)["summary"]
    assert summary["fiber"] == 35.8                 # it used to be 0.0 whatever was eaten
    assert summary["quality_score"] == 100          # fibre now counts towards the score


@pytest.mark.parametrize("sweets_g, flagged", [(50, False), (55, False), (56, True), (90, True)])
def test_added_sugar_above_a_tenth_of_energy(app, user, profile, sweets_g, flagged):
    # 2000 kcal of other food; sugar is 4 kcal a gram: 55 g is 9.9% of the energy, 56 g is 10.07%.
    base = with_calories(2000)
    base.append(item("candy", "sweets", sweets_g * 4.0, 0, 0, sweets_g, fiber=0, sugar=sweets_g, saturated_fat=0, salt=0.0,
                     grams=sweets_g))
    total_kcal = 2000 + sweets_g * 4.0
    share = sweets_g * 4.0 / total_kcal
    assert (share > 0.10) == flagged
    log(user, base)
    assert bool(of_type(recommend(user), "sugar")) == flagged


def test_sugar_of_fruit_and_milk_is_not_added_sugar(app, user, profile):
    day = with_calories(2000)
    day.append(item("fruit", "fruits", 400, 2, 0, 100, fiber=10, sugar=95, saturated_fat=0, salt=0.0, grams=600))
    day.append(item("milk", "dairy", 300, 15, 10, 25, fiber=0, sugar=24, saturated_fat=6, salt=0.3, grams=500))
    log(user, day)
    assert not of_type(recommend(user), "sugar")


def test_saturated_fat_above_a_tenth_of_energy(app, user, profile):
    # 2759 kcal of food of which 340 g x 9 = 3060 would be too much; 31 g x 9 = 279 kcal is 10.1%.
    day = with_calories(2759)
    day[0]["saturated_fat"] = 31.0
    log(user, day)
    assert of_type(recommend(user), "saturated_fat")
    db.session.query(MealItem).delete()
    db.session.query(Meal).delete()
    db.session.commit()
    ok = with_calories(2759)
    ok[0]["saturated_fat"] = 29.0
    log(user, ok)
    assert not of_type(recommend(user), "saturated_fat")


def test_hydration_advice_late_in_the_day_only_when_clearly_short(app, user, profile):
    log(user, balanced())
    # Goal 3.09 L; 80% = 2.472 L
    add_water_service(user.id, 2.4, DAY)
    assert of_type(recommend(user, LATE), "hydration")[0]["params"] == {"value": 0.7}
    assert not of_type(recommend(user, MORNING), "hydration")
    add_water_service(user.id, 0.1, DAY)       # 2.5 L
    assert not of_type(recommend(user, LATE), "hydration")


def test_no_hydration_advice_without_a_goal(app, user):
    db.session.add(UserProfile(user_id=user.id, training_location="home", weight=None, height=180, age=30))
    db.session.commit()
    log(user, balanced())
    assert not of_type(recommend(user), "hydration")


# --- quality --------------------------------------------------------------

def test_a_mostly_processed_day_is_called_out(app, user, profile):
    day = with_calories(2759)
    day[2]["category"] = "sweets"     # 2259 of the 2759 kcal
    day[2]["name"] = "cookies"
    log(user, day)
    assert [r["message_key"] for r in of_type(recommend(user), "quality")] == [
        "recommendations.items.quality.processed.message"
    ]


def test_processed_share_boundary_is_a_majority_of_classified_energy(app, user, profile):
    def day(sweets_kcal):
        return [
            item("chicken", "poultry", 1000, 100, 10, 0, fiber=0, sugar=0, saturated_fat=1, salt=0.5, grams=500),
            item("fruit", "fruits", 1000 - sweets_kcal + 1000, 1, 0, 25, fiber=40, sugar=30, saturated_fat=0, salt=0.0, grams=600),
            item("cookies", "sweets", sweets_kcal, 0, 0, 0, fiber=10, sugar=0, saturated_fat=0, salt=0.0, grams=100),
        ]

    # total 3000 kcal; 1500 processed is exactly half: not more than half
    log(user, day(1500))
    assert not [r for r in of_type(recommend(user), "quality")
                if r["message_key"].endswith("processed.message")]
    db.session.query(MealItem).delete()
    db.session.query(Meal).delete()
    db.session.commit()
    log(user, day(1501))
    assert [r for r in of_type(recommend(user), "quality")
            if r["message_key"].endswith("processed.message")]


def test_little_whole_food_is_a_gentle_nudge(app, user, profile):
    day = [
        item("rice", "grains", 1500, 30, 3, 330, fiber=2, sugar=1, saturated_fat=1, salt=0.1, grams=1000),
        item("pasta", "pasta", 1000, 35, 5, 200, fiber=2, sugar=1, saturated_fat=1, salt=0.1, grams=800),
        item("apple", "fruits", 250, 1, 0, 60, fiber=10, sugar=40, saturated_fat=0, salt=0.0, grams=450),
    ]   # whole = 250 / 2750 = 9%
    log(user, day)
    (found,) = of_type(recommend(user), "quality")
    assert found["message_key"] == "recommendations.items.quality.whole_foods.message"
    assert found["priority"] == "low"


def test_the_old_catch_all_score_trigger_is_gone(app, user, profile):
    # A day that scores low only for lack of data used to trigger "score < 45".
    day = [item(n, "other", 800, 40, 20, 100, fiber=None, sugar=None, saturated_fat=None, salt=None)
           for n in ("a", "b", "c")]
    log(user, day)
    result = recommend(user)
    assert not of_type(result, "quality")
    assert result["summary"]["quality_score"] is None


def test_composition_is_not_judged_on_a_few_entries_or_a_barely_eaten_day(app, user, profile):
    two = with_calories(2759)[:2]
    two[0]["calories"] = 2300
    log(user, two)
    assert not {"quality", "sugar", "saturated_fat", "fiber"} & set(types(recommend(user)))
    db.session.query(MealItem).delete()
    db.session.query(Meal).delete()
    db.session.commit()
    sweets = with_calories(1000)
    sweets[2]["category"] = "sweets"
    log(user, sweets)        # 1000 kcal is 36% of the target: far under, composition not judged
    result = recommend(user)
    assert of_type(result, "calories") and not of_type(result, "quality")


# --- determinism ----------------------------------------------------------

def test_same_data_same_advice_in_a_stable_order(app, user, profile):
    day = with_calories(1000)
    day[0]["salt"] = 6
    day[0]["protein"] = 20
    log(user, day)
    first = recommend(user)
    assert recommend(user) == first
    priorities = [r["priority"] for r in first["recommendations"]]
    assert priorities == sorted(priorities, key=["high", "medium", "low"].index)
    assert len({(r["type"], r["message_key"]) for r in first["recommendations"]}) == len(first["recommendations"])
    assert len(first["recommendations"]) <= rec.MAX_RECOMMENDATIONS


def test_the_endpoint_serves_the_same_result(app, user, client, profile):
    log(user, balanced())
    client.post("/auth/login", data={"email": user.email, "password": "password123"})
    body = client.get("/api/nutrition/recommendations").get_json()
    assert set(body) == {"recommendations", "summary"}
    assert {"calories_goal", "fiber", "quality_score", "day_progress", "water", "water_goal",
            "goals_available"} <= set(body["summary"])


def test_goal_type_comes_from_the_profile_in_its_canonical_form(app, user, profile):
    from backend.app.models import User

    for raw, canonical in (("fat_loss", "cut"), ("strength", "strength"), ("recomp", "recomp"),
                           ("muscle_gain", "gain")):
        profile.goal = raw
        db.session.commit()
        from backend.app.services.nutrition.calories_service import get_goal

        assert get_goal(User.query.get(user.id)) == canonical


# --- fibre advice needs a complete figure (M2) -------------------------------

def fibre_day(fibers):
    """Three entries of equal energy with the given fibre values (None = unknown)."""
    return [
        item(name, "legumes", 920, 45, 10, 100, fiber=fiber, sugar=1, saturated_fat=1, salt=0.2, grams=300)
        for name, fiber in zip("abc", fibers)
    ]


def fibre_advice(user, fibers):
    log(user, fibre_day(fibers))
    result = recommend(user)
    return result, of_type(result, "fiber")


def test_no_fibre_advice_when_the_fibre_is_only_partly_known(app, user, profile):
    # 0 g stated for two thirds of the energy, unknown for the rest: only a lower bound.
    result, found = fibre_advice(user, [0.0, 0.0, None])
    assert found == []
    assert result["summary"]["fiber"] == 0.0 and result["summary"]["fiber_complete"] is False


def test_fibre_advice_when_the_fibre_is_fully_known_and_short(app, user, profile):
    result, found = fibre_advice(user, [2.0, 3.0, 4.0])      # 9 g of 30 g
    assert [r["params"] for r in found] == [{"value": 21}]
    assert result["summary"]["fiber_complete"] is True


def test_a_genuine_zero_is_a_known_value_and_gets_advice(app, user, profile):
    result, found = fibre_advice(user, [0.0, 0.0, 0.0])
    assert [r["params"] for r in found] == [{"value": 30}]
    assert result["summary"]["fiber"] == 0.0 and result["summary"]["fiber_complete"] is True


def test_no_fibre_advice_when_the_fibre_is_missing_altogether(app, user, profile):
    result, found = fibre_advice(user, [None, None, None])
    assert found == []
    assert result["summary"]["fiber"] is None and result["summary"]["fiber_complete"] is False


def test_no_fibre_advice_when_the_target_is_met(app, user, profile):
    _, found = fibre_advice(user, [8.0, 8.0, 8.0])           # 24 g = 80% of 30 g: not short
    assert found == []


def test_one_unknown_entry_silences_fibre_advice_however_low_the_known_part(app, user, profile):
    for fibers in ([0.0, 0.0, None], [0.0, None, 0.0], [None, 1.0, 1.0]):
        db.session.query(MealItem).delete()
        db.session.query(Meal).delete()
        db.session.commit()
        _, found = fibre_advice(user, fibers)
        assert found == [], fibers
