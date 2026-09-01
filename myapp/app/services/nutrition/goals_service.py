from myapp.app.models.nutrition.plan import NutritionPlan
from myapp.app.models.nutrition.user_goals import UserGoals


def get_goals(user_id):
    goals = UserGoals.query.filter_by(
        user_id=user_id,
    ).first()

    if goals:
        return {
            "calories": goals.calories_goal,
            "protein": goals.protein_goal,
            "fat": goals.fat_goal,
            "carbs": goals.carb_goal,
        }

    plan = NutritionPlan.query.filter_by(
        user_id=user_id,
    ).first()

    if plan:
        return {
            "calories": plan.calories,
            "protein": plan.protein,
            "fat": plan.fats,
            "carbs": plan.carbs,
        }

    return {
        "calories": 0,
        "protein": 0,
        "fat": 0,
        "carbs": 0,
    }
