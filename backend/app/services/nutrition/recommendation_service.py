"""Nutrition recommendations for today.

Every recommendation is an i18n key plus parameters (the clients translate
them); nothing here produces text. The rules, their thresholds and where each
threshold comes from are listed in ``docs/nutrition-model.md``. Principles:

* Advice needs data it can rely on. No target -> no target-based advice
  (a ``profile_incomplete`` hint instead); a nutrient that is unknown for
  most of the energy -> no advice about it; a day with too little energy
  logged -> no judgement of its composition.
* Rules about the end of the day (totals compared with targets) only fire in
  the evening, when the day is nearly over; salt is the exception because a
  limit already exceeded stays exceeded.
* The result is deterministic for the same data and the same ``now``: rules
  run in a fixed order and are ranked by priority with a stable sort.
* "Today" and the hour come from the application's timezone
  (``backend.app.utils.clock``), never the server's.
"""
from __future__ import annotations

from sqlalchemy.orm import selectinload

from backend.app.models import Meal, User
from backend.app.services.nutrition.calculation_service import partial_totals
from backend.app.services.nutrition.calories_service import get_goal
from backend.app.services.nutrition.day_service import CALORIE_TOLERANCE
from backend.app.services.nutrition.goals_service import get_goals
from backend.app.services.nutrition.quality_service import (
    PROCESSED_SHARE_LIMIT,
    SATURATED_FAT_ENERGY_LIMIT,
    SUGAR_ENERGY_LIMIT,
    WHOLE_SHARE_TARGET,
    calculate_quality,
    quality_items,
)
from backend.app.services.nutrition.water_service import (
    get_total_fluid_liters,
    water_goal_for_user,
)
from backend.app.utils import clock

# Day phases by local hour (product policy).
EVENING_HOUR = 18
LATE_EVENING_HOUR = 21

# A total is "short" when it is below target by more than this share (the
# same order of magnitude as the logging tolerance of the calorie status).
SHORTFALL_TOLERANCE = 0.20
# Intake this far under the target is "well under" (three tolerances).
CALORIES_WELL_UNDER = 0.70

# Protein pacing in the afternoon: advise when more than this share of the
# target is still to eat.
PROTEIN_REMAINING_SHARE = 0.40

# Hydration estimates are rough (see water_service), so the advice only
# appears when clearly short.
HYDRATION_SHORTFALL = SHORTFALL_TOLERANCE

# WHO: less than 5 g of salt per day.
SALT_DAILY_LIMIT_G = 5.0

# Fat/carbohydrate balance: percentage points of macro energy the actual
# split may differ from the target split.
MACRO_SPLIT_TOLERANCE = 0.12

# Composition rules (quality, sugar, saturated fat, fibre) need this many
# logged entries.
MIN_ITEMS_FOR_COMPOSITION = 3

MAX_RECOMMENDATIONS = 5

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def _get_day_progress(now):
    hour = now.hour

    if hour < 12:
        return "morning"

    if hour < EVENING_HOUR:
        return "day"

    if hour < LATE_EVENING_HOUR:
        return "evening"

    return "late"


def _add_recommendation(
    recommendations,
    recommendation_type,
    title_key,
    message_key,
    priority,
    params=None,
):
    recommendations.append(
        {
            "type": recommendation_type,
            "title_key": title_key,
            "message_key": message_key,
            "params": params or {},
            "priority": priority,
        }
    )


def _today_entries(user_id, today):
    meals = (
        Meal.query.options(selectinload(Meal.items))
        .filter_by(user_id=user_id, date=today)
        .order_by(Meal.time.asc().nullsfirst(), Meal.id.asc())
        .all()
    )
    return [item for meal in meals for item in meal.items]


def _totals(entries):
    fiber, fiber_complete = partial_totals(entries, "fiber")
    salt, salt_complete = partial_totals(entries, "salt")
    return {
        "calories": sum(item.calories or 0 for item in entries),
        "protein": sum(item.protein or 0 for item in entries),
        "fat": sum(item.fat or 0 for item in entries),
        "carbs": sum(item.carbs or 0 for item in entries),
        "fiber": fiber if entries else None,
        "fiber_complete": fiber_complete,
        # Known salt only: a lower bound when some entries do not state it.
        "salt": salt if entries else None,
        "salt_complete": salt_complete,
    }


def _macro_split(protein, fat, carbs):
    energy = protein * 4 + fat * 9 + carbs * 4
    if energy <= 0:
        return None
    return {
        "protein": protein * 4 / energy,
        "fat": fat * 9 / energy,
        "carbs": carbs * 4 / energy,
    }


def _calorie_recommendation(recommendations, totals, goals, goal_type):
    goal = goals["calories"]
    ratio = totals["calories"] / goal

    if ratio < CALORIES_WELL_UNDER:
        _add_recommendation(
            recommendations,
            "calories",
            "recommendations.items.calories.low.title",
            "recommendations.items.calories.low.message",
            "medium",
        )
    elif ratio < 1 - CALORIE_TOLERANCE:
        # Under the target is the plan on a fat-loss goal: no nudge to eat.
        if goal_type != "cut":
            _add_recommendation(
                recommendations,
                "calories",
                "recommendations.items.calories.remaining.title",
                "recommendations.items.calories.remaining.message",
                "low",
                {"value": round(goal - totals["calories"])},
            )
    elif ratio > 1 + CALORIE_TOLERANCE:
        _add_recommendation(
            recommendations,
            "calories",
            "recommendations.items.calories.excess.title",
            "recommendations.items.calories.excess.message",
            "medium",
            {"value": round(totals["calories"] - goal)},
        )


def get_nutrition_recommendations(user_id, now=None):
    if now is None:
        now = clock.now()
    elif now.tzinfo is not None:
        # A moment given in another zone is read as the user's wall clock.
        now = now.astimezone(clock.app_timezone())
    today = now.date()

    user = User.query.get(user_id)
    goals = get_goals(user_id)
    goals_available = goals["available"]
    entries = _today_entries(user_id, today)
    totals = _totals(entries)
    quality = calculate_quality(quality_items(entries), goals)
    day_progress = _get_day_progress(now)
    closing = day_progress in ("evening", "late")
    goal_type = get_goal(user) if user is not None else None
    water = get_total_fluid_liters(user_id, today)
    water_goal = water_goal_for_user(user_id, today)

    recommendations = []

    if not entries:
        _add_recommendation(
            recommendations,
            "balance",
            "recommendations.items.empty.title",
            "recommendations.items.empty.message",
            "low",
        )
    else:
        if not goals_available:
            _add_recommendation(
                recommendations,
                "profile",
                "recommendations.items.profile_incomplete.title",
                "recommendations.items.profile_incomplete.message",
                "low",
            )

        calorie_ratio = (
            totals["calories"] / goals["calories"] if goals_available else None
        )
        # A day that is far from complete says little about composition.
        composition_judgeable = (
            quality["reason"] is None
            and len(entries) >= MIN_ITEMS_FOR_COMPOSITION
            and (calorie_ratio is None or calorie_ratio >= CALORIES_WELL_UNDER)
        )

        protein_flagged = False

        if goals_available and day_progress == "day":
            remaining = max(goals["protein"] - totals["protein"], 0)
            if remaining > goals["protein"] * PROTEIN_REMAINING_SHARE:
                _add_recommendation(
                    recommendations,
                    "protein_progress",
                    "recommendations.items.protein_progress.title",
                    "recommendations.items.protein_progress.message",
                    "low",
                    {"value": round(remaining)},
                )

        if closing and goals_available:
            _calorie_recommendation(recommendations, totals, goals, goal_type)

            if totals["protein"] < goals["protein"] * (1 - SHORTFALL_TOLERANCE):
                protein_flagged = True
                _add_recommendation(
                    recommendations,
                    "protein",
                    "recommendations.items.macro_insufficient.title",
                    "recommendations.items.macro_insufficient.message",
                    "high" if day_progress == "late" else "medium",
                    {
                        "value": round(goals["protein"] - totals["protein"]),
                        "macro": "protein",
                    },
                )

        # Salt: an exceeded daily limit stays exceeded, so any time of day,
        # and the known part of the salt is enough to say so.
        if totals["salt"] is not None and totals["salt"] > SALT_DAILY_LIMIT_G:
            _add_recommendation(
                recommendations,
                "salt",
                "recommendations.items.salt.high.title",
                "recommendations.items.salt.high.message",
                "medium",
                {"value": round(totals["salt"], 1), "limit": SALT_DAILY_LIMIT_G},
            )

        if closing and composition_judgeable:
            components = quality["components"]

            fiber = components.get("fiber")
            # Only on a complete figure: with some entries missing their fibre
            # the known part is a lower bound, and "short" cannot be claimed.
            if (
                fiber is not None
                and totals["fiber_complete"]
                and totals["fiber"] is not None
                and totals["fiber"] < goals["fiber"] * (1 - SHORTFALL_TOLERANCE)
            ):
                _add_recommendation(
                    recommendations,
                    "fiber",
                    "recommendations.items.fiber.low.title",
                    "recommendations.items.fiber.low.message",
                    "low",
                    {"value": round(goals["fiber"] - totals["fiber"])},
                )

            sugar = components.get("sugar")
            if sugar is not None and sugar["value"] > SUGAR_ENERGY_LIMIT:
                _add_recommendation(
                    recommendations,
                    "sugar",
                    "recommendations.items.sugar.high.title",
                    "recommendations.items.sugar.high.message",
                    "low",
                    {"value": round(sugar["value"] * 100)},
                )

            saturated = components.get("saturated_fat")
            if saturated is not None and saturated["value"] > SATURATED_FAT_ENERGY_LIMIT:
                _add_recommendation(
                    recommendations,
                    "saturated_fat",
                    "recommendations.items.saturated_fat.high.title",
                    "recommendations.items.saturated_fat.high.message",
                    "low",
                    {"value": round(saturated["value"] * 100)},
                )

            processed = components.get("processed_foods")
            whole = components.get("whole_foods")
            if processed is not None and processed["value"] > PROCESSED_SHARE_LIMIT:
                _add_recommendation(
                    recommendations,
                    "quality",
                    "recommendations.items.quality.processed.title",
                    "recommendations.items.quality.processed.message",
                    "medium",
                )
            elif whole is not None and whole["value"] < WHOLE_SHARE_TARGET / 2:
                _add_recommendation(
                    recommendations,
                    "quality",
                    "recommendations.items.quality.whole_foods.title",
                    "recommendations.items.quality.whole_foods.message",
                    "low",
                )

            if goals_available and not protein_flagged \
                    and abs(calorie_ratio - 1) <= CALORIE_TOLERANCE:
                _macro_balance(recommendations, totals, goals)

        if closing and water_goal is not None \
                and water < water_goal * (1 - HYDRATION_SHORTFALL):
            _add_recommendation(
                recommendations,
                "hydration",
                "recommendations.items.hydration.low.title",
                "recommendations.items.hydration.low.message",
                "low",
                {"value": round(water_goal - water, 1)},
            )

    recommendations.sort(key=lambda item: PRIORITY_ORDER[item["priority"]])
    recommendations = recommendations[:MAX_RECOMMENDATIONS]

    return {
        "recommendations": recommendations,
        "summary": {
            "calories": round(totals["calories"]),
            "calories_goal": goals["calories"],
            "protein": round(totals["protein"], 1),
            "protein_goal": goals["protein"],
            "fat": round(totals["fat"], 1),
            "fat_goal": goals["fat"],
            "carbs": round(totals["carbs"], 1),
            "carbs_goal": goals["carbs"],
            "fiber": (
                round(totals["fiber"], 1) if totals["fiber"] is not None else None
            ),
            "fiber_complete": totals["fiber_complete"],
            "fiber_goal": goals["fiber"],
            "water": water,
            "water_goal": water_goal,
            "quality_score": quality["score"],
            "goals_available": goals_available,
            "day_progress": day_progress,
        },
    }


def _macro_balance(recommendations, totals, goals):
    """Fat/carbohydrate split far from the target split (protein is covered
    by its own rule, and fat and carbohydrate targets are the energy left
    after protein, so only their split is compared)."""
    current = _macro_split(totals["protein"], totals["fat"], totals["carbs"])
    target = _macro_split(goals["protein"], goals["fat"], goals["carbs"])
    if current is None or target is None:
        return

    differences = {
        macro: abs(current[macro] - target[macro]) for macro in ("fat", "carbs")
    }
    largest = max(differences, key=differences.get)
    if differences[largest] < MACRO_SPLIT_TOLERANCE:
        return

    _add_recommendation(
        recommendations,
        "macro_balance",
        "recommendations.items.macro_balance.title",
        "recommendations.items.macro_balance.message",
        "low",
        {
            "macro": largest,
            "direction": "higher" if current[largest] > target[largest] else "lower",
        },
    )
