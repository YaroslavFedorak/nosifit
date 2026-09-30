from backend.app.extensions import db

from backend.app.models.user import User
from backend.app.models.nutrition.user_goals import UserGoals

from backend.app.services.nutrition.calories_service import (
    calculate_nutrition_goals,
)

DEFAULT_FIBER_GOAL = 30.0


def get_goals(user_id):
    user = User.query.get(user_id)

    if not user:
        return {
            "calories": 0,
            "protein": 0,
            "fat": 0,
            "carbs": 0,
            "fiber": DEFAULT_FIBER_GOAL,
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
                "fiber": goals.fiber_goal or DEFAULT_FIBER_GOAL,
            }

        return {
            "calories": 0,
            "protein": 0,
            "fat": 0,
            "carbs": 0,
            "fiber": DEFAULT_FIBER_GOAL,
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
    if not goals.fiber_goal:
        goals.fiber_goal = DEFAULT_FIBER_GOAL

    db.session.commit()

    calculated["fiber"] = goals.fiber_goal
    return calculated

