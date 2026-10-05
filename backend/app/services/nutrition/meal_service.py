from datetime import date, datetime, time

from backend.app.extensions import db
from backend.app.models import Meal, MealItem
from backend.app.services.nutrition.meal_categories import normalize_meal_category


def _parse_time(value):
    if value in (None, ""):
        return None

    if isinstance(value, time):
        return value

    try:
        return datetime.strptime(value, "%H:%M").time()
    except (TypeError, ValueError):
        return None


def _parse_date(value):
    if value in (None, ""):
        return None

    if isinstance(value, date):
        return value

    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def recalc_meal_totals(meal):
    meal.total_calories = sum(item.calories or 0 for item in meal.items)
    meal.total_protein = sum(item.protein or 0 for item in meal.items)
    meal.total_fat = sum(item.fat or 0 for item in meal.items)
    meal.total_carbs = sum(item.carbs or 0 for item in meal.items)
    meal.total_fiber = sum(item.fiber or 0 for item in meal.items)


def add_meal_service(user_id, data):
    category = normalize_meal_category(data.get("category")) or normalize_meal_category(data.get("name"))

    if category is None:
        raise ValueError("Unknown meal category")

    meal = Meal(
        user_id=user_id,
        date=_parse_date(data.get("date")) or date.today(),
        time=_parse_time(data.get("time")),
        name=category,
        category=category,
    )

    db.session.add(meal)
    db.session.commit()

    return meal


def update_meal_service(user_id, meal_id, data):
    meal = Meal.query.filter_by(id=meal_id, user_id=user_id).first()

    if meal is None:
        return None

    category = None

    if "category" in data:
        category = normalize_meal_category(data["category"])
    elif "name" in data:
        category = normalize_meal_category(data["name"])

    if category is not None:
        meal.category = category
        meal.name = category

    if "date" in data and data["date"]:
        try:
            meal.date = datetime.strptime(
                data["date"],
                "%Y-%m-%d",
            ).date()
        except (TypeError, ValueError):
            pass

    if "time" in data:
        meal.time = _parse_time(data["time"])

    db.session.commit()

    return meal


def delete_meal_service(user_id, meal_id):
    meal = Meal.query.filter_by(id=meal_id, user_id=user_id).first()

    if meal is None:
        return False

    db.session.delete(meal)
    db.session.commit()

    return True


def copy_meal_service(user_id, meal_id):
    source_meal = Meal.query.filter_by(
        id=meal_id,
        user_id=user_id,
    ).first()

    if source_meal is None:
        return None

    new_meal = Meal(
        user_id=user_id,
        date=date.today(),
        time=source_meal.time,
        name=source_meal.name,
        category=source_meal.category,
    )

    db.session.add(new_meal)
    db.session.flush()

    for source_item in source_meal.items:
        new_item = MealItem(
            meal_id=new_meal.id,
            product_id=source_item.product_id,
            name=source_item.name,
            amount=source_item.amount,
            unit=source_item.unit,
            weight=source_item.weight,
            calories=source_item.calories,
            protein=source_item.protein,
            fat=source_item.fat,
            carbs=source_item.carbs,
            fiber=source_item.fiber,
            liquid_ml=source_item.liquid_ml,
            category_id=source_item.category_id,
        )
        db.session.add(new_item)

    db.session.flush()
    recalc_meal_totals(new_meal)
    db.session.commit()

    return new_meal
