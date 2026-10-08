from datetime import date

from sqlalchemy import func

from backend.app.extensions import db
from backend.app.models import Meal, MealItem, User
from backend.app.models.nutrition.user_water import UserWater


def ml_per_kg_by_age(age):
    if age is None:
        return 35

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


def _apply_activity_adjustment(water, activity):
    activity_multipliers = {
        "low": 1.0,
        "moderate": 1.05,
        "high": 1.10,
        "very_high": 1.15,
    }

    if isinstance(activity, str):
        normalized_activity = activity.strip().lower()

        if normalized_activity in activity_multipliers:
            return water * activity_multipliers[normalized_activity]

        try:
            activity = float(normalized_activity)
        except (TypeError, ValueError):
            return water

    try:
        activity_value = float(activity)

        activity_value = max(
            1.0,
            min(activity_value, 2.0),
        )

        return water * (1 + (activity_value - 1.2) * 0.07)

    except (TypeError, ValueError):
        return water


def calculate_water(
    weight,
    height,
    age,
    gender,
    activity,
    goal,
):
    if not weight or weight <= 0:
        return 0.0

    ml_per_kg = ml_per_kg_by_age(age)

    water = weight * ml_per_kg / 1000

    if gender == "male":
        water *= 1.03

    water = _apply_activity_adjustment(
        water,
        activity,
    )

    if goal in (
        "lose",
        "fat_loss",
        "weight_loss",
    ):
        water *= 1.05

    elif goal in (
        "gain",
        "muscle_gain",
        "mass_gain",
    ):
        water *= 1.02

    water = max(
        1.5,
        min(water, 3.5),
    )

    return round(water, 2)


def get_total_fluid_liters(user_id, target_date=None):
    target_date = target_date or date.today()

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


def get_water_data(user_id):
    user = User.query.get(user_id)

    if user is None:
        return {
            "amount": 0.0,
            "recommended": 0.0,
        }

    profile = getattr(user, "profile", None)

    if profile is None:
        return {
            "amount": 0.0,
            "recommended": 0.0,
        }

    today = date.today()

    current_amount = get_total_fluid_liters(
        user_id,
        today,
    )

    recommended = calculate_water(
        weight=getattr(profile, "weight", None),
        height=getattr(profile, "height", None),
        age=getattr(profile, "age", None),
        gender=getattr(profile, "gender", None),
        activity=getattr(profile, "activity", None),
        goal=getattr(profile, "goal", None),
    )

    return {
        "amount": round(current_amount, 2),
        "recommended": recommended,
    }


def add_water_service(user_id, amount):
    today = date.today()

    entry = UserWater.query.filter_by(
        user_id=user_id,
        date=today,
    ).first()

    if entry is None:
        entry = UserWater(
            user_id=user_id,
            date=today,
            amount=0,
        )

        db.session.add(entry)

    # Negative amounts are corrections ("I logged too much"). The manual
    # total never goes below zero.
    entry.amount = max(0.0, round(float(entry.amount or 0) + amount, 3))

    db.session.commit()

    return entry

