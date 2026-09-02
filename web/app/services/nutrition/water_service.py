from datetime import date

from web.app import db
from web.app.models.nutrition.user_water import UserWater


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

    activity_multipliers = {
        "low": 1.0,
        "moderate": 1.05,
        "high": 1.10,
        "very_high": 1.15,
    }

    if isinstance(activity, str):
        water *= activity_multipliers.get(
            activity,
            1.0,
        )

    else:
        try:
            activity_value = float(activity)

            activity_value = max(
                1.0,
                min(activity_value, 2.0),
            )

            water *= 1 + (activity_value - 1.2) * 0.07

        except (TypeError, ValueError):
            pass

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

    entry.amount += amount

    db.session.commit()

    return entry
