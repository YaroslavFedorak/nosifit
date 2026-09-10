from web.app import db

from web.app.models.user import User
from web.app.models.nutrition.user_goals import UserGoals

from web.app.services.nutrition.calories_service import (
    calculate_nutrition_goals,
)


def get_goals(user_id):
    user = User.query.get(user_id)

    if not user:
        return {
            "calories": 0,
            "protein": 0,
            "fat": 0,
            "carbs": 0,
        }

    calculated = calculate_nutrition_goals(user)

    if calculated is None:
        goals = UserGoals.query.filter_by(
            user_id=user.id,
        ).first()

        if goals:
            return {
                "calories": goals.calories_goal or 0,
                "protein": goals.protein_goal or 0,
                "fat": goals.fat_goal or 0,
                "carbs": goals.carb_goal or 0,
            }

        return {
            "calories": 0,
            "protein": 0,
            "fat": 0,
            "carbs": 0,
        }

    goals = UserGoals.query.filter_by(
        user_id=user.id,
    ).first()

    if goals is None:
        goals = UserGoals(
            user_id=user.id,
        )
        db.session.add(goals)

    goals.calories_goal = calculated["calories"]
    goals.protein_goal = calculated["protein"]
    goals.fat_goal = calculated["fat"]
    goals.carb_goal = calculated["carbs"]

    db.session.commit()

    return calculated
