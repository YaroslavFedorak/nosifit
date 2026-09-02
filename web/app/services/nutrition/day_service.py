from datetime import date, timedelta

from web.app.models.nutrition.meal import Meal
from web.app.models.nutrition.user_water import UserWater
from web.app.models.user import User
from web.app.models.user_profile import UserProfile

from web.app.services.nutrition.goals_service import (
    get_goals,
)
from web.app.services.nutrition.quality_service import (
    calculate_quality,
)
from web.app.services.nutrition.serializers import (
    serialize_meal,
)
from web.app.services.nutrition.water_service import (
    calculate_water,
)


def safe_profile_value(profile, field, default):
    if profile is None:
        return default

    value = getattr(profile, field, None)

    if value in (None, ""):
        return default

    return value


def parse_float(value, default=0.0):
    try:
        if value is None:
            return default

        if isinstance(value, (int, float)):
            return float(value)

        return float(str(value).replace(",", ".").strip())

    except (TypeError, ValueError):
        return default


def calculate_percent(value, goal):
    if goal <= 0:
        return 0

    return round(
        value / goal * 100,
        1,
    )


def calculate_difference(current, previous):
    difference = current - previous

    if difference > 0:
        return f"+{round(difference, 1)}"

    return str(round(difference, 1))


def get_meal_totals(meals):
    return {
        "calories": sum(meal.total_calories or 0 for meal in meals),
        "protein": sum(meal.total_protein or 0 for meal in meals),
        "fat": sum(meal.total_fat or 0 for meal in meals),
        "carbs": sum(meal.total_carbs or 0 for meal in meals),
    }


def get_daily_nutrition_data(user_id):
    user = User.query.get(user_id)
    today = date.today()
    yesterday = today - timedelta(days=1)

    goals = get_goals(user_id)

    meals = (
        Meal.query.filter(
            Meal.user_id == user_id,
            Meal.date == today,
        )
        .order_by(
            Meal.time.asc().nullsfirst(),
            Meal.id.asc(),
        )
        .all()
    )

    yesterday_meals = Meal.query.filter(
        Meal.user_id == user_id,
        Meal.date == yesterday,
    ).all()

    totals = get_meal_totals(meals)
    yesterday_totals = get_meal_totals(yesterday_meals)

    progress = {
        "calories": totals["calories"],
        "protein": totals["protein"],
        "fat": totals["fat"],
        "carbs": totals["carbs"],
        "calories_percent": calculate_percent(
            totals["calories"],
            goals["calories"],
        ),
        "protein_percent": calculate_percent(
            totals["protein"],
            goals["protein"],
        ),
        "fat_percent": calculate_percent(
            totals["fat"],
            goals["fat"],
        ),
        "carbs_percent": calculate_percent(
            totals["carbs"],
            goals["carbs"],
        ),
    }

    total_macros = totals["protein"] + totals["fat"] + totals["carbs"]

    if total_macros > 0:
        macros_ratio = {
            "protein": round(
                totals["protein"] / total_macros * 100,
                1,
            ),
            "fat": round(
                totals["fat"] / total_macros * 100,
                1,
            ),
            "carbs": round(
                totals["carbs"] / total_macros * 100,
                1,
            ),
        }

    else:
        macros_ratio = {
            "protein": 0,
            "fat": 0,
            "carbs": 0,
        }

    ration_items = [
        {
            "id": item.id,
            "name": item.name,
            "calories": item.calories,
            "protein": item.protein,
            "fat": item.fat,
            "carbs": item.carbs,
            "fiber": item.fiber,
        }
        for meal in meals
        for item in meal.items
    ]

    quality = calculate_quality(ration_items)

    calorie_balance = totals["calories"] - goals["calories"]

    if calorie_balance > 150:
        balance_status = "Перебір"

    elif calorie_balance < -150:
        balance_status = "Недобір"

    else:
        balance_status = "Норма"

    profile = UserProfile.query.filter_by(user_id=user_id).first()

    weight = parse_float(
        safe_profile_value(
            profile,
            "weight",
            0,
        )
    )

    height = parse_float(
        safe_profile_value(
            profile,
            "height",
            170,
        )
    )

    age = int(
        parse_float(
            safe_profile_value(
                profile,
                "age",
                25,
            )
        )
    )

    gender = safe_profile_value(
        profile,
        "gender",
        "male",
    )

    activity = safe_profile_value(
        profile,
        "activity",
        "low",
    )

    goal = safe_profile_value(
        profile,
        "goal",
        "maintain",
    )

    water_goal = calculate_water(
        weight=weight,
        height=height,
        age=age,
        gender=gender,
        activity=activity,
        goal=goal,
    )

    water_entry = UserWater.query.filter_by(
        user_id=user_id,
        date=today,
    ).first()

    water_today = water_entry.amount if water_entry else 0

    water_percent = calculate_percent(
        water_today,
        water_goal,
    )

    return {
        "meals": [serialize_meal(meal) for meal in meals],
        "goals": goals,
        "progress": progress,
        "macros_ratio": macros_ratio,
        "quality": quality,
        "current_weight": (
            user.profile.weight
            if (user and user.profile and user.profile.weight is not None)
            else None
        ),
        "kcal": totals["calories"],
        "kcal_goal": goals["calories"],
        "kcal_percent": (progress["calories_percent"]),
        "kcal_balance": calorie_balance,
        "protein": totals["protein"],
        "protein_goal": goals["protein"],
        "protein_percent": (progress["protein_percent"]),
        "fat": totals["fat"],
        "fat_goal": goals["fat"],
        "fat_percent": (progress["fat_percent"]),
        "carb": totals["carbs"],
        "carb_goal": goals["carbs"],
        "carb_percent": (progress["carbs_percent"]),
        "balance_status": balance_status,
        "kcal_yesterday": (yesterday_totals["calories"]),
        "protein_yesterday": (yesterday_totals["protein"]),
        "fat_yesterday": (yesterday_totals["fat"]),
        "carb_yesterday": (yesterday_totals["carbs"]),
        "kcal_diff_label": (
            calculate_difference(
                totals["calories"],
                yesterday_totals["calories"],
            )
        ),
        "protein_diff_label": (
            calculate_difference(
                totals["protein"],
                yesterday_totals["protein"],
            )
        ),
        "fat_diff_label": (
            calculate_difference(
                totals["fat"],
                yesterday_totals["fat"],
            )
        ),
        "carb_diff_label": (
            calculate_difference(
                totals["carbs"],
                yesterday_totals["carbs"],
            )
        ),
        "water": water_today,
        "water_goal": water_goal,
        "water_percent": water_percent,
    }
