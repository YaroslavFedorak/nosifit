from datetime import date, timedelta

from web.app.models import Meal, UserWeight
from web.app.models.nutrition.user_water import UserWater
from web.app.models.user_profile import UserProfile

from web.app.services.nutrition.goals_service import (
    get_goals,
)

from web.app.services.nutrition.water_service import (
    calculate_water,
)


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
        calories_by_date.setdefault(
            meal.date,
            0,
        )

        calories_by_date[meal.date] += meal.total_calories or 0

    labels = []
    kcal_values = []

    for i in range(days):
        current_date = start_date + timedelta(days=i)

        labels.append(current_date.strftime("%d.%m"))

        kcal_values.append(
            calories_by_date.get(
                current_date,
                0,
            )
        )

    weights = (
        UserWeight.query.filter_by(
            user_id=user_id,
        )
        .order_by(UserWeight.date.asc())
        .all()
    )

    weight_labels = [entry.date.strftime("%d.%m") for entry in weights]

    weight_values = [entry.weight for entry in weights]

    goals = get_goals(user_id)

    avg_kcal = round(sum(kcal_values) / len(kcal_values)) if kcal_values else 0

    return {
        "kcal": {
            "labels": labels,
            "values": kcal_values,
        },
        "weight": {
            "labels": weight_labels,
            "values": weight_values,
        },
        "avg_kcal": avg_kcal,
        "goal_kcal": goals["calories"],
        "current_weight": (weight_values[-1] if weight_values else None),
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

    calories_by_date = {}
    protein_by_date = {}
    fat_by_date = {}
    carbs_by_date = {}

    for meal in meals:
        calories_by_date.setdefault(
            meal.date,
            0,
        )

        protein_by_date.setdefault(
            meal.date,
            0,
        )

        fat_by_date.setdefault(
            meal.date,
            0,
        )

        carbs_by_date.setdefault(
            meal.date,
            0,
        )

        calories_by_date[meal.date] += meal.total_calories or 0

        protein_by_date[meal.date] += meal.total_protein or 0

        fat_by_date[meal.date] += meal.total_fat or 0

        carbs_by_date[meal.date] += meal.total_carbs or 0

    goals = get_goals(user_id)

    calorie_goal = goals.get(
        "calories",
        0,
    )

    protein_goal = goals.get(
        "protein",
        0,
    )

    fat_goal = goals.get(
        "fat",
        0,
    )

    carbs_goal = goals.get(
        "carbs",
        0,
    )

    today = date.today()

    days = []

    current_date = start

    while current_date <= end:
        kcal = calories_by_date.get(
            current_date,
            0,
        )

        protein = protein_by_date.get(
            current_date,
            0,
        )

        fat = fat_by_date.get(
            current_date,
            0,
        )

        carbs = carbs_by_date.get(
            current_date,
            0,
        )

        if current_date > today:
            percent = 0
            level = 0

        else:
            percent = round(kcal / calorie_goal * 100) if calorie_goal > 0 else 0

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
                "kcal": kcal,
                "protein": round(protein, 1),
                "fat": round(fat, 1),
                "carbs": round(carbs, 1),
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

    return {
        "year": year,
        "days": days,
    }


def get_day_details(user_id, target_date):
    meals = (
        Meal.query.filter(
            Meal.user_id == user_id,
            Meal.date == target_date,
        )
        .order_by(
            Meal.time.asc(),
            Meal.id.asc(),
        )
        .all()
    )

    total_calories = 0
    total_protein = 0
    total_fat = 0
    total_carbs = 0

    serialized_meals = []

    for meal in meals:
        calories = meal.total_calories or 0
        protein = meal.total_protein or 0
        fat = meal.total_fat or 0
        carbs = meal.total_carbs or 0

        total_calories += calories
        total_protein += protein
        total_fat += fat
        total_carbs += carbs

        items = []

        for item in meal.items:
            items.append(
                {
                    "id": item.id,
                    "name": item.name,
                    "weight": item.weight,
                    "calories": item.calories or 0,
                    "protein": item.protein or 0,
                    "fat": item.fat or 0,
                    "carbs": item.carbs or 0,
                    "fiber": item.fiber or 0,
                    "category_id": item.category_id,
                }
            )

        serialized_meals.append(
            {
                "id": meal.id,
                "name": meal.name,
                "category": meal.category,
                "time": (meal.time.strftime("%H:%M") if meal.time else None),
                "total_calories": calories,
                "total_protein": protein,
                "total_fat": fat,
                "total_carbs": carbs,
                "items": items,
            }
        )

    goals = get_goals(user_id)

    water_entry = UserWater.query.filter_by(
        user_id=user_id,
        date=target_date,
    ).first()

    water_amount = float(water_entry.amount) if water_entry is not None else 0.0

    profile = UserProfile.query.filter_by(
        user_id=user_id,
    ).first()

    if profile is not None:
        water_goal = calculate_water(
            weight=getattr(
                profile,
                "weight",
                None,
            ),
            height=getattr(
                profile,
                "height",
                None,
            ),
            age=getattr(
                profile,
                "age",
                None,
            ),
            gender=getattr(
                profile,
                "gender",
                None,
            ),
            activity=getattr(
                profile,
                "activity",
                None,
            ),
            goal=getattr(
                profile,
                "goal",
                None,
            ),
        )
    else:
        water_goal = 0.0

    weight_entry = UserWeight.query.filter_by(
        user_id=user_id,
        date=target_date,
    ).first()

    current_weight = float(weight_entry.weight) if weight_entry is not None else None

    return {
        "date": target_date.isoformat(),
        "calories": total_calories,
        "protein": round(total_protein, 1),
        "fat": round(total_fat, 1),
        "carbs": round(total_carbs, 1),
        "calorie_goal": goals.get(
            "calories",
            0,
        ),
        "protein_goal": goals.get(
            "protein",
            0,
        ),
        "fat_goal": goals.get(
            "fat",
            0,
        ),
        "carbs_goal": goals.get(
            "carbs",
            0,
        ),
        "water": round(
            water_amount,
            2,
        ),
        "water_goal": water_goal,
        "current_weight": current_weight,
        "meals": serialized_meals,
    }
