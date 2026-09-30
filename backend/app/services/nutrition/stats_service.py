from datetime import date, timedelta

from backend.app.models import Meal, UserWeight
from backend.app.models.nutrition.user_water import UserWater
from backend.app.models.user_profile import UserProfile
from backend.app.services.nutrition.goals_service import get_goals
from backend.app.services.nutrition.product_service import normalize_locale
from backend.app.services.nutrition.serializers import serialize_meal
from backend.app.services.nutrition.water_service import calculate_water


def get_stats(user_id, days=7):
    today = date.today()
    start_date = today - timedelta(days=days - 1)

    meals = Meal.query.filter(
        Meal.user_id == user_id,
        Meal.date >= start_date,
        Meal.date <= today,
    ).all()

    calories_by_date = {}
    for meal in meals:
        calories_by_date.setdefault(meal.date, 0)
        calories_by_date[meal.date] += meal.total_calories or 0

    labels = []
    kcal_values = []

    for i in range(days):
        current_date = start_date + timedelta(days=i)
        labels.append(current_date.strftime("%d.%m"))
        kcal_values.append(calories_by_date.get(current_date, 0))

    weights = (
        UserWeight.query
        .filter_by(user_id=user_id)
        .order_by(UserWeight.date.asc())
        .all()
    )

    weight_labels = [entry.date.strftime("%d.%m") for entry in weights]
    weight_values = [entry.weight for entry in weights]
    goals = get_goals(user_id)

    avg_kcal = round(sum(kcal_values) / len(kcal_values)) if kcal_values else 0

    return {
        "kcal": {"labels": labels, "values": kcal_values},
        "weight": {"labels": weight_labels, "values": weight_values},
        "avg_kcal": avg_kcal,
        "goal_kcal": goals["calories"],
        "current_weight": weight_values[-1] if weight_values else None,
        "weight_trend": "Стабільно",
    }


def get_year_heatmap(user_id, year):
    start = date(year, 1, 1)
    end = date(year, 12, 31)

    meals = Meal.query.filter(
        Meal.user_id == user_id,
        Meal.date >= start,
        Meal.date <= end,
    ).all()

    totals_by_date = {}

    for meal in meals:
        totals = totals_by_date.setdefault(
            meal.date,
            {"calories": 0, "protein": 0, "fat": 0, "carbs": 0},
        )
        totals["calories"] += meal.total_calories or 0
        totals["protein"] += meal.total_protein or 0
        totals["fat"] += meal.total_fat or 0
        totals["carbs"] += meal.total_carbs or 0

    goals = get_goals(user_id)
    calorie_goal = goals.get("calories", 0)
    protein_goal = goals.get("protein", 0)
    fat_goal = goals.get("fat", 0)
    carbs_goal = goals.get("carbs", 0)
    today = date.today()

    days = []
    current_date = start

    while current_date <= end:
        totals = totals_by_date.get(
            current_date,
            {"calories": 0, "protein": 0, "fat": 0, "carbs": 0},
        )

        if current_date > today:
            percent = 0
            level = 0
        else:
            percent = (
                round(totals["calories"] / calorie_goal * 100)
                if calorie_goal > 0
                else 0
            )

            if percent == 0:
                level = 0
            elif percent <= 25:
                level = 1
            elif percent <= 50:
                level = 2
            elif percent <= 75:
                level = 3
            elif percent <= 100:
                level = 4
            elif percent <= 125:
                level = 5
            else:
                level = 6

        days.append(
            {
                "date": current_date.isoformat(),
                "kcal": totals["calories"],
                "protein": round(totals["protein"], 1),
                "fat": round(totals["fat"], 1),
                "carbs": round(totals["carbs"], 1),
                "calorie_goal": calorie_goal,
                "protein_goal": protein_goal,
                "fat_goal": fat_goal,
                "carbs_goal": carbs_goal,
                "percent": percent,
                "level": level,
                "is_today": current_date == today,
            }
        )

        current_date += timedelta(days=1)

    return {"year": year, "days": days}


def get_day_details(user_id, target_date, locale="uk"):
    locale = normalize_locale(locale)
    meals = (
        Meal.query
        .filter(
            Meal.user_id == user_id,
            Meal.date == target_date,
        )
        .order_by(Meal.time.asc(), Meal.id.asc())
        .all()
    )

    totals = {
        "calories": 0,
        "protein": 0,
        "fat": 0,
        "carbs": 0,
        "fiber": 0,
    }

    serialized_meals = [serialize_meal(meal, locale) for meal in meals]

    goals = get_goals(user_id)

    water_entry = UserWater.query.filter_by(
        user_id=user_id,
        date=target_date,
    ).first()

    water_amount = float(water_entry.amount) if water_entry else 0.0

    profile = UserProfile.query.filter_by(user_id=user_id).first()
    water_goal = (
        calculate_water(
            weight=getattr(profile, "weight", None),
            height=getattr(profile, "height", None),
            age=getattr(profile, "age", None),
            gender=getattr(profile, "gender", None),
            activity=getattr(profile, "activity", None),
            goal=getattr(profile, "goal", None),
        )
        if profile is not None
        else 0.0
    )

    weight_entry = UserWeight.query.filter_by(
        user_id=user_id,
        date=target_date,
    ).first()

    return {
        "date": target_date.isoformat(),
        "calories": totals["calories"],
        "protein": round(totals["protein"], 1),
        "fat": round(totals["fat"], 1),
        "carbs": round(totals["carbs"], 1),
        "fiber": round(totals["fiber"], 1),
        "fiber_goal": goals.get("fiber", 30),
        "calorie_goal": goals.get("calories", 0),
        "protein_goal": goals.get("protein", 0),
        "fat_goal": goals.get("fat", 0),
        "carbs_goal": goals.get("carbs", 0),
        "water": round(water_amount, 2),
        "water_goal": water_goal,
        "current_weight": (
            float(weight_entry.weight)
            if weight_entry is not None
            else None
        ),
        "meals": serialized_meals,
    }
