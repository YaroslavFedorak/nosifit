from web.app import db

from web.app.models.user import User
from web.app.models.nutrition.plan import NutritionPlan
from web.app.models.nutrition.user_goals import UserGoals

from web.app.services.nutrition.calories_service import (
    calculate_nutrition_goals,
)


def get_goals(user_id):
    goals = UserGoals.query.filter_by(user_id=user_id).first()

    if goals:
        has_valid_goals = (
            goals.calories_goal > 0
            and goals.protein_goal > 0
            and goals.fat_goal > 0
            and goals.carb_goal > 0
        )

        if has_valid_goals:
            return {
                "calories": goals.calories_goal,
                "protein": goals.protein_goal,
                "fat": goals.fat_goal,
                "carbs": goals.carb_goal,
            }

    plan = NutritionPlan.query.filter_by(user_id=user_id).first()

    if plan:
        has_valid_plan = (
            plan.calories > 0 and plan.protein > 0 and plan.fats > 0 and plan.carbs > 0
        )

        if has_valid_plan:
            return {
                "calories": plan.calories,
                "protein": plan.protein,
                "fat": plan.fats,
                "carbs": plan.carbs,
            }

    user = User.query.get(user_id)

    if user:
        calculated = calculate_nutrition_goals(user)

        if calculated:
            if goals is None:
                goals = UserGoals(user_id=user.id)
                db.session.add(goals)

            goals.calories_goal = calculated["calories"]
            goals.protein_goal = calculated["protein"]
            goals.fat_goal = calculated["fat"]
            goals.carb_goal = calculated["carbs"]

            db.session.commit()

            return calculated

    return {
        "calories": 0,
        "protein": 0,
        "fat": 0,
        "carbs": 0,
    }
