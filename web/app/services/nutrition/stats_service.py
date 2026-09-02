from datetime import date, timedelta

from web.app.models import Meal, UserWeight

from web.app.services.nutrition.goals_service import (
    get_goals,
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
        UserWeight.query.filter_by(user_id=user_id)
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

    for meal in meals:
        calories_by_date.setdefault(
            meal.date,
            0,
        )

        calories_by_date[meal.date] += meal.total_calories or 0

    goals = get_goals(user_id)

    goal_calories = goals["calories"]

    days = []

    current_date = start

    while current_date <= end:
        kcal = calories_by_date.get(
            current_date,
            0,
        )

        percent = round(kcal / goal_calories * 100) if goal_calories > 0 else 0

        if percent == 0:
            level = 0

        elif percent <= 25:
            level = 1

        elif percent <= 50:
            level = 2

        elif percent <= 75:
            level = 3

        else:
            level = 4

        days.append(
            {
                "date": current_date.isoformat(),
                "kcal": kcal,
                "percent": percent,
                "level": level,
            }
        )

        current_date += timedelta(days=1)

    return {
        "year": year,
        "days": days,
    }
