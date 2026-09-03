from datetime import date

from web.app.models import Meal

from web.app.services.nutrition.goals_service import (
    get_goals,
)
from web.app.services.nutrition.quality_service import (
    calculate_quality,
)


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


def get_nutrition_recommendations(user_id):
    meals = _get_today_meals(user_id)
    items = _get_today_items(meals)

    goals = get_goals(user_id)
    totals = _calculate_totals(items)
    quality = calculate_quality(items)

    recommendations = []

    calories_goal = goals.get("calories", 0) or 0
    protein_goal = goals.get("protein", 0) or 0

    calories = totals["calories"]
    protein = totals["protein"]
    fiber = totals["fiber"]

    if calories_goal > 0:
        calorie_ratio = calories / calories_goal

        if calorie_ratio < 0.6:
            _add_recommendation(
                recommendations,
                "calories",
                "Недостатнє споживання калорій",
                "На цей момент ви спожили менше 60% добової калорійності. Варто додати повноцінний прийом їжі.",
                "high",
            )

        elif calorie_ratio < 0.85:
            _add_recommendation(
                recommendations,
                "calories",
                "Калорійність нижча за ціль",
                "Поточне споживання калорій нижче вашої добової цілі. Зверніть увагу на наступний прийом їжі.",
                "medium",
            )

        elif calorie_ratio > 1.15:
            _add_recommendation(
                recommendations,
                "calories",
                "Перевищення калорійності",
                "Поточне споживання калорій перевищує добову ціль більш ніж на 15%.",
                "medium",
            )

    if protein_goal > 0:
        protein_ratio = protein / protein_goal

        if protein_ratio < 0.6:
            _add_recommendation(
                recommendations,
                "protein",
                "Низьке споживання білка",
                "Спожито менше 60% вашої добової цілі білка. Додайте джерело білка до наступного прийому їжі.",
                "high",
            )

        elif protein_ratio < 0.85:
            _add_recommendation(
                recommendations,
                "protein",
                "Білок нижче цілі",
                "Поточне споживання білка нижче запланованого рівня.",
                "medium",
            )

    if fiber < 20:
        _add_recommendation(
            recommendations,
            "fiber",
            "Низьке споживання клітковини",
            "Додайте овочі, фрукти, бобові або цільнозернові продукти, щоб збільшити споживання клітковини.",
            "medium",
        )

    if quality["processed_foods_percent"] >= 25:
        _add_recommendation(
            recommendations,
            "quality",
            "Висока частка оброблених продуктів",
            "Спробуйте замінити частину оброблених продуктів на більш поживні цільні продукти.",
            "medium",
        )

    if quality["whole_foods_percent"] < 50 and items:
        _add_recommendation(
            recommendations,
            "quality",
            "Покращте якість раціону",
            "Збільшіть частку овочів, фруктів, круп, бобових, риби, м'яса та інших цільних продуктів.",
            "low",
        )

    if not items:
        _add_recommendation(
            recommendations,
            "balance",
            "Почніть вести харчовий журнал",
            "Додайте перший прийом їжі, щоб NosiFit міг оцінити ваш поточний раціон.",
            "low",
        )

    priority_order = {
        "high": 0,
        "medium": 1,
        "low": 2,
    }

    recommendations.sort(key=lambda item: priority_order[item["priority"]])

    return {
        "recommendations": recommendations,
        "summary": {
            "calories": calories,
            "calories_goal": calories_goal,
            "protein": protein,
            "protein_goal": protein_goal,
            "fiber": round(fiber),
            "quality_score": quality["score"],
        },
    }
