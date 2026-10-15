from datetime import timedelta

from sqlalchemy.orm import selectinload

from backend.app.models import Meal, MealItem, Product
from backend.app.models.user_profile import UserProfile

from backend.app.services.nutrition.calculation_service import partial_totals
from backend.app.services.nutrition.goals_service import get_goals
from backend.app.services.nutrition.quality_service import (
    calculate_quality,
    quality_items,
)
from backend.app.services.nutrition.product_service import normalize_locale
from backend.app.services.nutrition.serializers import serialize_meal
from backend.app.services.nutrition.water_service import (
    get_total_fluid_liters,
    water_goal_for_user,
)
from backend.app.utils import clock

# A day is "on target" within this share of the calorie target either way.
# Product policy: logged intake is never exact (portion sizes, label error),
# so a few percent either way is not a miss. The recommendations use the same
# tolerance.
CALORIE_TOLERANCE = 0.10


def calculate_percent(value, goal):
    """Share of the target in percent; ``None`` when there is no target."""
    if goal is None or goal <= 0:
        return None
    return round(value / goal * 100, 1)


def calorie_status(consumed, goal, has_entries):
    """Where the day's calories stand against the target.

    ``unavailable`` - no target (profile incomplete): nothing to compare to;
    ``no_data`` - nothing logged yet; otherwise ``under`` / ``normal`` /
    ``over`` with :data:`CALORIE_TOLERANCE`.
    """
    if goal is None or goal <= 0:
        return "unavailable"
    if not has_entries:
        return "no_data"
    balance = consumed - goal
    if balance > goal * CALORIE_TOLERANCE:
        return "over"
    if balance < -goal * CALORIE_TOLERANCE:
        return "under"
    return "normal"


def calculate_difference(current, previous):
    difference = current - previous
    return f"+{round(difference, 1)}" if difference > 0 else str(round(difference, 1))


def get_meal_totals(meals):
    return {
        "calories": sum(meal.total_calories or 0 for meal in meals),
        "protein": sum(meal.total_protein or 0 for meal in meals),
        "fat": sum(meal.total_fat or 0 for meal in meals),
        "carbs": sum(meal.total_carbs or 0 for meal in meals),
        "fiber": sum(meal.total_fiber or 0 for meal in meals),
    }


def get_partial_totals(meals):
    """Fiber and sugar of the day, keeping "unknown" apart from 0.

    Needs ``meal.items`` loaded (the day queries eager-load them).
    """
    items = [item for meal in meals for item in meal.items]
    fiber, fiber_complete = partial_totals(items, "fiber")
    sugar, sugar_complete = partial_totals(items, "sugar")
    return {
        "fiber": fiber,
        "fiber_complete": fiber_complete,
        "sugar": sugar,
        "sugar_complete": sugar_complete,
    }


def meal_load_options():
    return (
        selectinload(Meal.items)
        .selectinload(MealItem.product)
        .selectinload(Product.names)
    )


def load_meal_for_display(meal_id):
    """The meal with its entries, products and names in three queries.

    Freshly committed objects would lazy-load each product (N+1).
    """
    return Meal.query.options(meal_load_options()).filter_by(id=meal_id).one()


def get_daily_nutrition_data(user_id, locale="uk"):
    locale = normalize_locale(locale)
    today = clock.today()
    yesterday = today - timedelta(days=1)
    goals = get_goals(user_id)
    goals_available = goals["available"]

    meals = (
        Meal.query
        .options(meal_load_options())
        .filter(Meal.user_id == user_id, Meal.date == today)
        .order_by(Meal.time.asc().nullsfirst(), Meal.id.asc())
        .all()
    )

    yesterday_meals = Meal.query.filter(
        Meal.user_id == user_id,
        Meal.date == yesterday,
    ).all()

    totals = get_meal_totals(meals)
    totals.update(get_partial_totals(meals))
    yesterday_totals = get_meal_totals(yesterday_meals)

    percents = {
        key: calculate_percent(totals[key], goals[key])
        for key in ("calories", "protein", "fat", "carbs")
    }

    progress = {
        "calories": totals["calories"],
        "protein": round(totals["protein"], 1),
        "fat": round(totals["fat"], 1),
        "carbs": round(totals["carbs"], 1),
        "fiber": totals["fiber"],
        "fiber_complete": totals["fiber_complete"],
        "sugar": totals["sugar"],
        "sugar_complete": totals["sugar_complete"],
        "calories_percent": percents["calories"],
        "protein_percent": percents["protein"],
        "fat_percent": percents["fat"],
        "carbs_percent": percents["carbs"],
    }

    total_macros = totals["protein"] + totals["fat"] + totals["carbs"]
    if total_macros > 0:
        macros_ratio = {
            "protein": round(totals["protein"] / total_macros * 100, 1),
            "fat": round(totals["fat"] / total_macros * 100, 1),
            "carbs": round(totals["carbs"] / total_macros * 100, 1),
        }
    else:
        macros_ratio = {"protein": 0, "fat": 0, "carbs": 0}

    entries = [item for meal in meals for item in meal.items]
    quality = calculate_quality(quality_items(entries), goals)

    calorie_balance = (
        totals["calories"] - goals["calories"] if goals_available else None
    )
    balance_status = calorie_status(
        totals["calories"], goals["calories"], bool(entries)
    )

    water_goal = water_goal_for_user(user_id, today)
    water_today = get_total_fluid_liters(user_id, today)
    water_percent = calculate_percent(water_today, water_goal)

    profile = UserProfile.query.filter_by(user_id=user_id).first()

    return {
        "meals": [serialize_meal(meal, locale) for meal in meals],
        "goals": goals,
        "goals_available": goals_available,
        "progress": progress,
        "macros_ratio": macros_ratio,
        "quality": quality,
        "current_weight": (
            profile.weight
            if profile is not None and profile.weight is not None
            else None
        ),
        "kcal": totals["calories"],
        "kcal_goal": goals["calories"],
        "kcal_percent": progress["calories_percent"],
        "kcal_balance": calorie_balance,
        "kcal_remaining": (
            max(goals["calories"] - totals["calories"], 0)
            if goals_available else None
        ),
        "protein": progress["protein"],
        "protein_goal": goals["protein"],
        "protein_percent": progress["protein_percent"],
        "fat": progress["fat"],
        "fat_goal": goals["fat"],
        "fat_percent": progress["fat_percent"],
        "carb": progress["carbs"],
        "carb_goal": goals["carbs"],
        "carb_percent": progress["carbs_percent"],
        "fiber": totals["fiber"],
        "fiber_complete": totals["fiber_complete"],
        "fiber_goal": goals["fiber"],
        "sugar": totals["sugar"],
        "sugar_complete": totals["sugar_complete"],
        "balance_status": balance_status,
        "kcal_yesterday": yesterday_totals["calories"],
        "protein_yesterday": yesterday_totals["protein"],
        "fat_yesterday": yesterday_totals["fat"],
        "carb_yesterday": yesterday_totals["carbs"],
        "kcal_diff_label": calculate_difference(
            totals["calories"],
            yesterday_totals["calories"],
        ),
        "protein_diff_label": calculate_difference(
            totals["protein"],
            yesterday_totals["protein"],
        ),
        "fat_diff_label": calculate_difference(
            totals["fat"],
            yesterday_totals["fat"],
        ),
        "carb_diff_label": calculate_difference(
            totals["carbs"],
            yesterday_totals["carbs"],
        ),
        "water": water_today,
        "water_goal": water_goal,
        "water_percent": water_percent,
    }
