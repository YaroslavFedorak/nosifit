"""Daily fluid goal and fluid intake.

What the numbers mean
---------------------
* **Goal** - an estimate of the fluid a person should drink in a day
  (``fluid`` = drinks, not the water inside solid food), in litres. It is a
  starting point, not a medical requirement: needs vary with food, climate,
  exercise, illness and medication.
* **Intake** - manual water entries plus the fluid of logged drinks
  (``MealItem.liquid_ml``), in litres.

Formula (all in :func:`calculate_water`)
----------------------------------------
``weight (kg) x ml/kg(age) / 1000``, then

* x 1.03 for men (more lean mass at the same weight; no factor for women or
  when the sex is not given),
* x an activity factor (sedentary 1.00, light 1.025, moderate 1.05,
  active 1.10, very active 1.15: higher sweat losses; a product heuristic,
  not a measured value; unknown activity -> no adjustment). The stored value
  may be a label or a factor such as "1.375" (see ``activity_level``),

clamped to 1.5-3.5 L. The 30-45 ml/kg by age is the common
"30-40 ml per kg" rule of thumb, higher for children; the 1.5 L floor is
close to the EFSA adequate intake of water from drinks (about 1.6 L for
women, 2.0 L for men, EFSA 2010). Fat-loss and muscle-gain goals do not
change the estimate: nothing supports a goal-specific fluid requirement.

Missing data
------------
Weight is required: without a usable weight there is **no** goal (``None``),
never 0. A missing or implausible age is replaced by the adult default
(35 ml/kg); a missing sex or activity simply gets no adjustment. Those are
the only fallbacks.

One path: every screen (day, history, statistics, dashboard) gets the goal
from :func:`water_goal_for_user`.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func

from backend.app.extensions import db
from backend.app.models import Meal, MealItem, User
from backend.app.models.nutrition.user_water import UserWater
from backend.app.models.nutrition.user_weight import UserWeight
from backend.app.models.user_profile import UserProfile
from backend.app.services.nutrition.calories_service import activity_level
from backend.app.utils import clock
from backend.app.utils.validation import PROFILE_RANGES

MIN_GOAL_LITERS = 1.5
MAX_GOAL_LITERS = 3.5
MALE_FACTOR = 1.03
DEFAULT_ML_PER_KG = 35.0

# Keyed by the canonical levels of ``calories_service.activity_level``.
ACTIVITY_FACTORS = {
    "sedentary": 1.00,
    "light": 1.025,
    "moderate": 1.05,
    "active": 1.10,
    "very_active": 1.15,
}

# How far back a water entry may be added for a past day.
MAX_BACKFILL_DAYS = 365


class WaterValidationError(ValueError):
    pass


def ml_per_kg_by_age(age):
    """Fluid per kg of body weight for an age; the adult default when unknown."""
    if age is None:
        return DEFAULT_ML_PER_KG

    if age <= 12:
        return 45

    if 13 <= age <= 17:
        return 45 - (age - 12) * (7 / 5)

    if 18 <= age <= 25:
        return 38 - (age - 17) * (2 / 8)

    if 26 <= age <= 40:
        return 36 - (age - 25) * (1 / 15)

    if 41 <= age <= 60:
        return 35 - (age - 40) * (2 / 20)

    return max(
        30,
        33 - (age - 60) * (3 / 40),
    )


def activity_factor(activity) -> float:
    """The multiplier for a stored activity value (label or factor); 1.0 when unknown."""
    return ACTIVITY_FACTORS.get(activity_level(activity), 1.0)


def _number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def calculate_water(weight, age=None, gender=None, activity=None):
    """The daily fluid goal in litres, or ``None`` when it cannot be given.

    ``None`` (never 0) when the weight is missing or outside the range a
    profile accepts. Rounded once, at the end.
    """
    weight = _number(weight)
    low, high, _ = PROFILE_RANGES["weight"]
    if weight is None or not low <= weight <= high:
        return None

    age = _number(age)
    age_low, age_high, _ = PROFILE_RANGES["age"]
    if age is not None and not age_low <= age <= age_high:
        age = None

    liters = weight * ml_per_kg_by_age(age) / 1000.0

    if isinstance(gender, str) and gender.strip().lower() == "male":
        liters *= MALE_FACTOR

    liters *= activity_factor(activity)

    return round(max(MIN_GOAL_LITERS, min(liters, MAX_GOAL_LITERS)), 2)


def _weight_on(user_id, target_date, profile):
    """The weight to use for ``target_date``.

    Today (and any day without a weighing on or before it) uses the profile's
    current weight; a past day uses the last weighing up to that day, so
    history is not rewritten by today's weight.
    """
    if target_date < clock.today():
        entry = (
            UserWeight.query.filter(
                UserWeight.user_id == user_id,
                UserWeight.date <= target_date,
            )
            .order_by(UserWeight.date.desc())
            .first()
        )
        if entry is not None:
            return entry.weight
    return getattr(profile, "weight", None)


def water_goal_for_user(user_id, target_date=None, profile=None):
    """The fluid goal of a user for a day, or ``None`` when not available."""
    target_date = target_date or clock.today()
    if profile is None:
        profile = UserProfile.query.filter_by(user_id=user_id).first()
    if profile is None:
        return None
    return calculate_water(
        weight=_weight_on(user_id, target_date, profile),
        age=profile.age,
        gender=profile.gender,
        activity=profile.activity,
    )


def get_total_fluid_liters(user_id, target_date=None):
    """Manual water plus the fluid of logged drinks for a day, in litres."""
    target_date = target_date or clock.today()

    manual_entry = UserWater.query.filter_by(
        user_id=user_id,
        date=target_date,
    ).first()

    manual_liters = (
        float(manual_entry.amount)
        if manual_entry is not None
        else 0.0
    )

    liquid_ml = (
        db.session.query(
            func.coalesce(func.sum(MealItem.liquid_ml), 0.0)
        )
        .join(Meal, Meal.id == MealItem.meal_id)
        .filter(
            Meal.user_id == user_id,
            Meal.date == target_date,
        )
        .scalar()
        or 0.0
    )

    return round(manual_liters + float(liquid_ml) / 1000.0, 2)


def fluids_by_day(user_id, start: date, end: date) -> dict:
    """Total fluid in litres for each day of ``start..end`` that has any.

    Two queries for the whole range; the sum per day is the same as
    :func:`get_total_fluid_liters`.
    """
    totals = {}
    for day, amount in (
        db.session.query(UserWater.date, UserWater.amount)
        .filter(
            UserWater.user_id == user_id,
            UserWater.date >= start,
            UserWater.date <= end,
        )
        .all()
    ):
        totals[day] = totals.get(day, 0.0) + float(amount or 0)
    for day, liquid_ml in (
        db.session.query(Meal.date, func.coalesce(func.sum(MealItem.liquid_ml), 0.0))
        .join(MealItem, MealItem.meal_id == Meal.id)
        .filter(
            Meal.user_id == user_id,
            Meal.date >= start,
            Meal.date <= end,
        )
        .group_by(Meal.date)
        .all()
    ):
        totals[day] = totals.get(day, 0.0) + float(liquid_ml or 0) / 1000.0
    return {day: round(amount, 2) for day, amount in totals.items()}


def get_water_data(user_id, target_date=None):
    """Intake and goal of a day (today by default).

    ``recommended`` is ``None`` when the goal cannot be calculated (no usable
    weight); ``recommended_available`` says the same in one flag.
    """
    target_date = target_date or clock.today()

    if db.session.get(User, user_id) is None:
        return {
            "amount": 0.0,
            "recommended": None,
            "recommended_available": False,
            "date": target_date.isoformat(),
            "kind": "fluids",
        }

    recommended = water_goal_for_user(user_id, target_date)

    return {
        "amount": round(get_total_fluid_liters(user_id, target_date), 2),
        "recommended": recommended,
        "recommended_available": recommended is not None,
        "date": target_date.isoformat(),
        "kind": "fluids",
    }


def validate_water_date(target_date):
    """``target_date`` must be a day that can still be logged."""
    today = clock.today()
    if target_date > today:
        raise WaterValidationError("Date cannot be in the future")
    if target_date < today - timedelta(days=MAX_BACKFILL_DAYS):
        raise WaterValidationError(
            f"Date cannot be more than {MAX_BACKFILL_DAYS} days back"
        )


def add_water_service(user_id, amount, target_date=None):
    """Add (or, negative, subtract) manual water on a day; today by default."""
    target_date = target_date or clock.today()
    validate_water_date(target_date)

    entry = UserWater.query.filter_by(
        user_id=user_id,
        date=target_date,
    ).first()

    if entry is None:
        entry = UserWater(
            user_id=user_id,
            date=target_date,
            amount=0,
        )

        db.session.add(entry)

    # Negative amounts are corrections ("I logged too much"). The manual
    # total never goes below zero.
    entry.amount = max(0.0, round(float(entry.amount or 0) + amount, 3))

    db.session.commit()

    return entry
