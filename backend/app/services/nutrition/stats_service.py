"""Nutrition history: the calorie/weight chart data, the year heatmap and one day.

Definitions (see ``docs/nutrition-model.md``)
---------------------------------------------
* **Logged day** - a day with at least one logged entry. A day without
  entries is *unknown* (``None`` in the chart values), not a day of 0 kcal.
* **Average intake** - the mean of the logged days with energy in the window.
  Today is left out as soon as an earlier day is logged, because a day in
  progress is not a full intake; it is used only when it is the only day.
* **Targets of a day** - the targets stored for that day
  (``goals_service.goals_for_day``), not today's.
* **Weight trend** - see :func:`weight_trend`.
"""
from __future__ import annotations

from datetime import date, timedelta
from statistics import median

from sqlalchemy import func
from sqlalchemy.orm import selectinload

from backend.app.extensions import db
from backend.app.models import Meal, MealItem, Product, UserWeight
from backend.app.services.nutrition.day_service import (
    calculate_percent,
    calorie_status,
    get_partial_totals,
)
from backend.app.services.nutrition.goals_service import (
    get_goals,
    goals_for_day,
    goals_timeline,
)
from backend.app.services.nutrition.product_service import normalize_locale
from backend.app.services.nutrition.quality_service import (
    calculate_quality,
    quality_items,
)
from backend.app.services.nutrition.serializers import serialize_meal
from backend.app.services.nutrition.water_service import (
    get_total_fluid_liters,
    water_goal_for_user,
)
from backend.app.utils import clock
from backend.app.utils.validation import PROFILE_RANGES

# Weight trend (product policy). Body weight moves by about half a kilogram
# or more from one day to the next (water, glycogen, gut content), so a
# change is only reported when the whole window moved more than that and at
# a pace of at least 0.1 kg a week.
TREND_MIN_DAYS = 14
TREND_MIN_MEASUREMENTS = 3
TREND_MIN_SPAN_DAYS = 7
TREND_MIN_CHANGE_KG = 0.5
TREND_MIN_KG_PER_WEEK = 0.1


def weight_trend(measurements):
    """Direction of body weight from ``[(date, kg), ...]``.

    The slope is the Theil-Sen estimate (the median of the slopes between
    every pair of measurements), so one wrong or unusual weighing does not
    move it, and measurements need not be daily. Returns a dict with
    ``direction`` - ``insufficient_data``, ``stable``, ``increasing`` or
    ``decreasing`` - and, when it could be calculated, ``change_kg`` over the
    measured span, ``kg_per_week``, ``span_days`` and ``measurements``.
    """
    low, high, _ = PROFILE_RANGES["weight"]
    points = sorted(
        {(day, float(kg)) for day, kg in measurements if kg is not None and low <= float(kg) <= high}
    )
    count = len(points)
    span = (points[-1][0] - points[0][0]).days if points else 0
    if count < TREND_MIN_MEASUREMENTS or span < TREND_MIN_SPAN_DAYS:
        return {"direction": "insufficient_data", "measurements": count, "span_days": span}

    slopes = [
        (points[j][1] - points[i][1]) / (points[j][0] - points[i][0]).days
        for i in range(count)
        for j in range(i + 1, count)
        if points[j][0] > points[i][0]
    ]
    slope = median(slopes)
    change = slope * span
    per_week = slope * 7

    if change >= TREND_MIN_CHANGE_KG and per_week >= TREND_MIN_KG_PER_WEEK:
        direction = "increasing"
    elif change <= -TREND_MIN_CHANGE_KG and per_week <= -TREND_MIN_KG_PER_WEEK:
        direction = "decreasing"
    else:
        direction = "stable"
    return {
        "direction": direction,
        "change_kg": round(change, 2),
        "kg_per_week": round(per_week, 2),
        "span_days": span,
        "measurements": count,
    }


def _daily_energy(user_id, start: date, end: date):
    """``{date: (kcal, entries)}`` for the days with entries, in one query."""
    rows = (
        db.session.query(
            Meal.date,
            func.coalesce(func.sum(MealItem.calories), 0),
            func.count(MealItem.id),
        )
        .join(MealItem, MealItem.meal_id == Meal.id)
        .filter(Meal.user_id == user_id, Meal.date >= start, Meal.date <= end)
        .group_by(Meal.date)
        .all()
    )
    return {day: (int(kcal), int(count)) for day, kcal, count in rows}


def average_logged_kcal(daily, today):
    """Mean kcal over days with logged energy, and how many days that is."""
    days = {day: kcal for day, (kcal, entries) in daily.items() if entries and kcal > 0}
    complete = {day: kcal for day, kcal in days.items() if day < today}
    used = complete or days
    if not used:
        return None, 0
    return round(sum(used.values()) / len(used)), len(used)


def get_stats(user_id, days=7):
    today = clock.today()
    start_date = today - timedelta(days=days - 1)

    daily = _daily_energy(user_id, start_date, today)

    labels = []
    kcal_values = []
    logged = []
    for i in range(days):
        current_date = start_date + timedelta(days=i)
        labels.append(current_date.strftime("%d.%m"))
        kcal, entries = daily.get(current_date, (0, 0))
        logged.append(entries > 0)
        kcal_values.append(kcal if entries > 0 else None)

    trend_start = today - timedelta(days=max(days, TREND_MIN_DAYS) - 1)
    trend_rows = (
        UserWeight.query
        .filter(
            UserWeight.user_id == user_id,
            UserWeight.date >= trend_start,
            UserWeight.date <= today,
        )
        .order_by(UserWeight.date.asc())
        .all()
    )
    weights = [entry for entry in trend_rows if entry.date >= start_date]
    latest = (
        UserWeight.query
        .filter(UserWeight.user_id == user_id, UserWeight.date <= today)
        .order_by(UserWeight.date.desc())
        .first()
    )
    goals = get_goals(user_id)
    average, average_days = average_logged_kcal(daily, today)
    trend = weight_trend([(entry.date, entry.weight) for entry in trend_rows])

    return {
        "kcal": {"labels": labels, "values": kcal_values, "logged": logged},
        "weight": {
            "labels": [entry.date.strftime("%d.%m") for entry in weights],
            "values": [entry.weight for entry in weights],
        },
        "avg_kcal": average,
        "avg_kcal_days": average_days,
        "goal_kcal": goals["calories"] if goals["available"] else None,
        "current_weight": latest.weight if latest is not None else None,
        "weight_trend": trend["direction"],
        "weight_trend_detail": trend,
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

    current_goals = get_goals(user_id)
    timeline = goals_timeline(user_id, start, end)
    today = clock.today()

    days = []
    current_date = start

    while current_date <= end:
        totals = totals_by_date.get(
            current_date,
            {"calories": 0, "protein": 0, "fat": 0, "carbs": 0},
        )
        goals = goals_for_day(timeline, current_goals, current_date)
        calorie_goal = goals["calories"] if goals["available"] else 0

        if current_date > today or not calorie_goal:
            percent = 0
            level = 0
        else:
            percent = round(totals["calories"] / calorie_goal * 100)

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
                "protein_goal": goals["protein"],
                "fat_goal": goals["fat"],
                "carbs_goal": goals["carbs"],
                "percent": percent,
                "level": level,
                "is_today": current_date == today,
                "goal_estimated": goals["estimated"],
            }
        )

        current_date += timedelta(days=1)

    return {"year": year, "days": days}


def get_day_details(user_id, target_date, locale="uk"):
    locale = normalize_locale(locale)
    meals = (
        Meal.query
        .options(
            selectinload(Meal.items)
            .selectinload(MealItem.product)
            .selectinload(Product.names)
        )
        .filter(
            Meal.user_id == user_id,
            Meal.date == target_date,
        )
        .order_by(Meal.time.asc(), Meal.id.asc())
        .all()
    )

    totals = {
        "calories": sum(meal.total_calories or 0 for meal in meals),
        "protein": sum(meal.total_protein or 0 for meal in meals),
        "fat": sum(meal.total_fat or 0 for meal in meals),
        "carbs": sum(meal.total_carbs or 0 for meal in meals),
    }
    totals.update(get_partial_totals(meals))

    serialized_meals = [serialize_meal(meal, locale) for meal in meals]

    current_goals = get_goals(user_id)
    goals = goals_for_day(
        goals_timeline(user_id, target_date, target_date), current_goals, target_date
    )

    water_amount = get_total_fluid_liters(
        user_id,
        target_date,
    )
    water_goal = water_goal_for_user(user_id, target_date)

    weight_entry = UserWeight.query.filter_by(
        user_id=user_id,
        date=target_date,
    ).first()

    entries = [item for meal in meals for item in meal.items]
    quality = calculate_quality(quality_items(entries), goals)

    return {
        "date": target_date.isoformat(),
        "calories": totals["calories"],
        "protein": round(totals["protein"], 1),
        "fat": round(totals["fat"], 1),
        "carbs": round(totals["carbs"], 1),
        "fiber": (
            round(totals["fiber"], 1) if totals["fiber"] is not None else None
        ),
        "fiber_complete": totals["fiber_complete"],
        "sugar": (
            round(totals["sugar"], 1) if totals["sugar"] is not None else None
        ),
        "sugar_complete": totals["sugar_complete"],
        "fiber_goal": goals["fiber"],
        "calorie_goal": goals["calories"],
        "protein_goal": goals["protein"],
        "fat_goal": goals["fat"],
        "carbs_goal": goals["carbs"],
        "goals_available": goals["available"],
        "goal_estimated": goals["estimated"],
        "balance_status": calorie_status(
            totals["calories"], goals["calories"], bool(entries)
        ),
        "quality": quality,
        "water": round(water_amount, 2),
        "water_goal": water_goal,
        "water_percent": calculate_percent(water_amount, water_goal),
        "current_weight": (
            float(weight_entry.weight)
            if weight_entry is not None
            else None
        ),
        "meals": serialized_meals,
    }
