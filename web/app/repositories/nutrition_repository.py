from web.app.models import Meal, MealItem
from datetime import date


def get_meals_for_day(user_id, day: date):
    return (
        Meal.query.filter_by(user_id=user_id, date=day)
        .order_by(Meal.time.asc().nullsfirst(), Meal.id.asc())
        .all()
    )


def get_meal_by_id(meal_id, user_id):
    return Meal.query.filter_by(id=meal_id, user_id=user_id).first()


def get_item_by_id(item_id, user_id):
    return (
        MealItem.query.join(Meal)
        .filter(MealItem.id == item_id, Meal.user_id == user_id)
        .first()
    )
