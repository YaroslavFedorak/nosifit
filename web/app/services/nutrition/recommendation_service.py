from datetime import date, datetime

from web.app.models import Meal, User

from web.app.services.nutrition.goals_service import (
    get_goals,
)
from web.app.services.nutrition.quality_service import (
    calculate_quality,
)

EVENING_HOUR = 18
LATE_EVENING_HOUR = 21

MACRO_TOLERANCE = 0.12
DAY_MACRO_TOLERANCE = 0.20
CALORIE_TOLERANCE = 0.10

MIN_ITEMS_FOR_DAY_ANALYSIS = 3
MIN_ITEMS_FOR_QUALITY_ANALYSIS = 3

DEFAULT_PROTEIN_PER_KG = {
    "loss": 1.6,
    "maintenance": 1.2,
    "gain": 1.6,
}

DEFAULT_FAT_PERCENT = 0.25
MIN_FAT_PERCENT = 0.20
MIN_CARBS_PERCENT = 0.30

MIN_WEIGHT_KG = 30.0
MAX_WEIGHT_KG = 300.0
FALLBACK_WEIGHT_KG = 70.0

MAX_RECOMMENDATIONS = 5


def _get_today_meals(user_id):
    return Meal.query.filter_by(
        user_id=user_id,
        date=date.today(),
    ).all()


def _get_today_items(meals):
    items = []

    for meal in meals:
        for item in meal.items:
            items.append(
                {
                    "name": item.name,
                    "calories": item.calories or 0,
                    "protein": item.protein or 0,
                    "fat": item.fat or 0,
                    "carbs": item.carbs or 0,
                    "fiber": item.fiber or 0,
                }
            )

    return items


def _calculate_totals(items):
    return {
        "calories": sum(item["calories"] for item in items),
        "protein": sum(item["protein"] for item in items),
        "fat": sum(item["fat"] for item in items),
        "carbs": sum(item["carbs"] for item in items),
        "fiber": sum(item["fiber"] for item in items),
    }


def _get_user_weight(user):
    weight = getattr(user, "weight", None)

    if weight is None:
        return FALLBACK_WEIGHT_KG

    try:
        weight = float(weight)
    except (TypeError, ValueError):
        return FALLBACK_WEIGHT_KG

    if weight < MIN_WEIGHT_KG or weight > MAX_WEIGHT_KG:
        return FALLBACK_WEIGHT_KG

    return weight


def _get_goal_type(user):
    goal = getattr(user, "goal", None)

    if not goal:
        return "maintenance"

    goal = str(goal).lower()

    if goal in (
        "loss",
        "lose",
        "weight_loss",
        "fat_loss",
        "схуднення",
    ):
        return "loss"

    if goal in (
        "gain",
        "muscle_gain",
        "weight_gain",
        "набір",
        "набір маси",
    ):
        return "gain"

    return "maintenance"


def _get_protein_target(user, goals):
    custom_target = float(goals.get("protein", 0) or 0)

    if custom_target > 0:
        return custom_target

    weight = _get_user_weight(user)
    goal_type = _get_goal_type(user)

    protein_per_kg = DEFAULT_PROTEIN_PER_KG.get(
        goal_type,
        DEFAULT_PROTEIN_PER_KG["maintenance"],
    )

    return round(weight * protein_per_kg, 1)


def _get_macro_targets(user, goals):
    calories_goal = float(goals.get("calories", 0) or 0)
    protein_goal = _get_protein_target(user, goals)
    custom_fat = float(goals.get("fat", 0) or 0)
    custom_carbs = float(goals.get("carbs", 0) or 0)

    if calories_goal <= 0:
        return {
            "calories": 0,
            "protein": round(protein_goal, 1),
            "fat": round(custom_fat, 1),
            "carbs": round(custom_carbs, 1),
            "fiber": 30,
        }

    protein_calories = protein_goal * 4
    available_calories = max(calories_goal - protein_calories, 0)

    if custom_fat > 0 or custom_carbs > 0:
        requested_fat_calories = (
            custom_fat * 9 if custom_fat > 0 else calories_goal * DEFAULT_FAT_PERCENT
        )

        requested_carbs_calories = (
            custom_carbs * 4 if custom_carbs > 0 else calories_goal * MIN_CARBS_PERCENT
        )

        requested_total = requested_fat_calories + requested_carbs_calories

        if requested_total > available_calories and requested_total > 0:
            scale = available_calories / requested_total

            fat_calories = requested_fat_calories * scale
            carbs_calories = requested_carbs_calories * scale
        else:
            fat_calories = requested_fat_calories
            carbs_calories = requested_carbs_calories

    else:
        preferred_fat_calories = calories_goal * DEFAULT_FAT_PERCENT
        minimum_fat_calories = calories_goal * MIN_FAT_PERCENT
        minimum_carbs_calories = calories_goal * MIN_CARBS_PERCENT

        if preferred_fat_calories + minimum_carbs_calories <= available_calories:
            fat_calories = preferred_fat_calories
            carbs_calories = available_calories - fat_calories

        elif minimum_fat_calories + minimum_carbs_calories <= available_calories:
            carbs_calories = minimum_carbs_calories
            fat_calories = available_calories - carbs_calories

        else:
            total_minimum = minimum_fat_calories + minimum_carbs_calories

            if total_minimum > 0:
                scale = available_calories / total_minimum

                fat_calories = minimum_fat_calories * scale
                carbs_calories = minimum_carbs_calories * scale
            else:
                fat_calories = 0
                carbs_calories = available_calories

    fat_goal = fat_calories / 9
    carbs_goal = carbs_calories / 4

    fiber_goal = max(25, round(calories_goal / 1000 * 14))

    return {
        "calories": round(calories_goal),
        "protein": round(protein_goal, 1),
        "fat": round(fat_goal, 1),
        "carbs": round(carbs_goal, 1),
        "fiber": fiber_goal,
    }


def _add_recommendation(
    recommendations,
    recommendation_type,
    title,
    message,
    priority,
):
    recommendations.append(
        {
            "type": recommendation_type,
            "title": title,
            "message": message,
            "priority": priority,
        }
    )


def _calculate_macro_distribution(totals):
    protein_calories = totals["protein"] * 4
    fat_calories = totals["fat"] * 9
    carbs_calories = totals["carbs"] * 4

    total_macro_calories = protein_calories + fat_calories + carbs_calories

    if total_macro_calories <= 0:
        return {"protein": 0, "fat": 0, "carbs": 0}

    return {
        "protein": protein_calories / total_macro_calories,
        "fat": fat_calories / total_macro_calories,
        "carbs": carbs_calories / total_macro_calories,
    }


def _calculate_target_distribution(targets):
    protein_calories = targets["protein"] * 4
    fat_calories = targets["fat"] * 9
    carbs_calories = targets["carbs"] * 4

    total_macro_calories = protein_calories + fat_calories + carbs_calories

    if total_macro_calories <= 0:
        return {"protein": 0, "fat": 0, "carbs": 0}

    return {
        "protein": protein_calories / total_macro_calories,
        "fat": fat_calories / total_macro_calories,
        "carbs": carbs_calories / total_macro_calories,
    }


def _get_day_progress():
    hour = datetime.now().hour

    if hour < 12:
        return "morning"

    if hour < EVENING_HOUR:
        return "day"

    if hour < LATE_EVENING_HOUR:
        return "evening"

    return "late"


def _build_progress_recommendations(
    recommendations,
    totals,
    targets,
    day_progress,
):
    if day_progress in ("morning", "day"):
        if targets["protein"] > 0:
            remaining = max(targets["protein"] - totals["protein"], 0)

            if remaining > targets["protein"] * 0.40:
                _add_recommendation(
                    recommendations,
                    "protein_progress",
                    "Залишився запас білка",
                    (
                        f"До вашої денної цілі залишилось "
                        f"близько {round(remaining)} г білка. "
                        f"Додайте джерело білка до наступних прийомів їжі."
                    ),
                    "low",
                )

        return

    _build_evening_macro_recommendations(
        recommendations,
        totals,
        targets,
        day_progress,
    )


def _build_evening_macro_recommendations(
    recommendations,
    totals,
    targets,
    day_progress,
):
    calories = totals["calories"]
    calories_goal = targets["calories"]

    if calories_goal > 0:
        calorie_ratio = calories / calories_goal

        if calorie_ratio < 0.70:
            _add_recommendation(
                recommendations,
                "calories",
                "Низька калорійність раціону",
                (
                    "До кінця дня ви спожили значно менше "
                    "калорій, ніж заплановано. Якщо ще планується "
                    "прийом їжі, варто зробити його більш поживним."
                ),
                "high",
            )

        elif calorie_ratio < (1 - CALORIE_TOLERANCE):
            remaining = max(calories_goal - calories, 0)

            _add_recommendation(
                recommendations,
                "calories",
                "Є запас до денної цілі",
                (
                    f"До орієнтовної денної цілі залишилось "
                    f"близько {round(remaining)} ккал."
                ),
                "medium",
            )

        elif calorie_ratio > (1 + CALORIE_TOLERANCE):
            excess = calories - calories_goal

            _add_recommendation(
                recommendations,
                "calories",
                "Перевищення денної калорійності",
                (
                    f"Поточне споживання перевищує ціль "
                    f"приблизно на {round(excess)} ккал."
                ),
                "medium",
            )

    macro_labels = {
        "protein": "білка",
        "fat": "жирів",
        "carbs": "вуглеводів",
    }

    macro_titles = {
        "protein": "Недостатньо білка",
        "fat": "Недостатньо жирів",
        "carbs": "Недостатньо вуглеводів",
    }

    for macro in ("protein", "fat", "carbs"):
        target = targets[macro]

        if target <= 0:
            continue

        current = totals[macro]
        ratio = current / target

        if ratio < 0.65:
            remaining = max(target - current, 0)

            priority = "high" if day_progress == "late" else "medium"

            _add_recommendation(
                recommendations,
                macro,
                macro_titles[macro],
                (
                    f"До орієнтовної цілі залишилось "
                    f"близько {round(remaining)} г "
                    f"{macro_labels[macro]}."
                ),
                priority,
            )


def _build_fiber_recommendation(
    recommendations,
    totals,
    targets,
    day_progress,
):
    fiber_goal = targets["fiber"]

    if fiber_goal <= 0:
        return

    fiber = totals["fiber"]
    ratio = fiber / fiber_goal

    if day_progress in ("morning", "day"):
        if ratio < 0.25:
            _add_recommendation(
                recommendations,
                "fiber",
                "Зверніть увагу на клітковину",
                (
                    "Протягом дня додайте овочі, фрукти, "
                    "бобові або цільнозернові продукти."
                ),
                "low",
            )

        return

    if ratio < 0.60:
        remaining = max(fiber_goal - fiber, 0)

        _add_recommendation(
            recommendations,
            "fiber",
            "Низьке споживання клітковини",
            (
                f"До орієнтовної цілі залишилось близько "
                f"{round(remaining)} г клітковини. "
                "Додайте овочі, фрукти, бобові або цільнозернові продукти."
            ),
            "medium",
        )


def _build_balance_recommendation(
    recommendations,
    totals,
    targets,
    items,
    day_progress,
):
    if not items:
        return

    if day_progress == "morning":
        return

    if day_progress == "day" and len(items) < MIN_ITEMS_FOR_DAY_ANALYSIS:
        return

    current_distribution = _calculate_macro_distribution(totals)
    target_distribution = _calculate_target_distribution(targets)

    differences = {}

    for macro in ("protein", "fat", "carbs"):
        differences[macro] = abs(
            current_distribution[macro] - target_distribution[macro]
        )

    largest_difference = max(differences, key=differences.get)
    difference = differences[largest_difference]

    tolerance = DAY_MACRO_TOLERANCE if day_progress == "day" else MACRO_TOLERANCE

    if difference < tolerance:
        return

    labels = {
        "protein": "білка",
        "fat": "жирів",
        "carbs": "вуглеводів",
    }

    current = current_distribution[largest_difference]
    target = target_distribution[largest_difference]

    direction = "вища" if current > target else "нижча"

    _add_recommendation(
        recommendations,
        "macro_balance",
        "Нерівномірний розподіл макронутрієнтів",
        (
            f"Частка {labels[largest_difference]} у поточному раціоні "
            f"помітно {direction} за орієнтовний баланс. "
            "Спробуйте зробити наступні прийоми їжі більш різноманітними."
        ),
        "low",
    )


def _build_quality_recommendations(
    recommendations,
    quality,
    items,
    day_progress,
):
    if not items:
        return

    if day_progress == "morning":
        return

    if day_progress == "day" and len(items) < MIN_ITEMS_FOR_QUALITY_ANALYSIS:
        return

    processed_percent = quality.get("processed_foods_percent", 0)
    whole_percent = quality.get("whole_foods_percent", 0)
    score = quality.get("score", 0)

    processed_threshold = 55 if day_progress == "day" else 40

    if processed_percent >= processed_threshold:
        _add_recommendation(
            recommendations,
            "quality",
            "Висока частка оброблених продуктів",
            (
                "Значну частину раціону складають оброблені продукти. "
                "Спробуйте частіше додавати цільні та мінімально оброблені продукти."
            ),
            "medium",
        )

    elif whole_percent < 40:
        _add_recommendation(
            recommendations,
            "quality",
            "Мало цільних продуктів",
            (
                "Для більш різноманітного раціону додайте овочі, "
                "фрукти, крупи, бобові та інші цільні продукти."
            ),
            "low",
        )

    elif score < 45:
        _add_recommendation(
            recommendations,
            "quality",
            "Є простір для покращення раціону",
            (
                "Спробуйте зробити раціон більш різноманітним "
                "та збільшити частку поживних цільних продуктів."
            ),
            "low",
        )


def _build_empty_state_recommendation(recommendations, items):
    if items:
        return

    _add_recommendation(
        recommendations,
        "balance",
        "Почніть вести харчовий журнал",
        (
            "Додайте перший прийом їжі, щоб NosiFit міг "
            "оцінити баланс вашого раціону та сформувати персональні рекомендації."
        ),
        "low",
    )


def _limit_recommendations(recommendations):
    priority_order = {"high": 0, "medium": 1, "low": 2}

    recommendations.sort(key=lambda item: priority_order[item["priority"]])

    return recommendations[:MAX_RECOMMENDATIONS]


def get_nutrition_recommendations(user_id):
    user = User.query.get(user_id)
    meals = _get_today_meals(user_id)
    items = _get_today_items(meals)
    goals = get_goals(user_id)

    totals = _calculate_totals(items)
    quality = calculate_quality(items)
    targets = _get_macro_targets(user, goals)
    day_progress = _get_day_progress()

    recommendations = []

    _build_empty_state_recommendation(recommendations, items)

    if items:
        _build_progress_recommendations(
            recommendations,
            totals,
            targets,
            day_progress,
        )

        _build_fiber_recommendation(
            recommendations,
            totals,
            targets,
            day_progress,
        )

        _build_balance_recommendation(
            recommendations,
            totals,
            targets,
            items,
            day_progress,
        )

        _build_quality_recommendations(
            recommendations,
            quality,
            items,
            day_progress,
        )

    recommendations = _limit_recommendations(recommendations)

    return {
        "recommendations": recommendations,
        "summary": {
            "calories": round(totals["calories"]),
            "calories_goal": targets["calories"],
            "protein": round(totals["protein"], 1),
            "protein_goal": targets["protein"],
            "fat": round(totals["fat"], 1),
            "fat_goal": targets["fat"],
            "carbs": round(totals["carbs"], 1),
            "carbs_goal": targets["carbs"],
            "fiber": round(totals["fiber"], 1),
            "fiber_goal": targets["fiber"],
            "quality_score": quality.get("score", 0),
            "day_progress": day_progress,
        },
    }
