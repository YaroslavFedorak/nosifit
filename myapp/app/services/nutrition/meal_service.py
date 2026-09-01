from datetime import date, datetime, time

from myapp.app import db
from myapp.app.models import Meal


def _parse_time(value):
    if value in (None, ""):
        return None

    if isinstance(value, time):
        return value

    try:
        return datetime.strptime(
            value,
            "%H:%M",
        ).time()
    except (TypeError, ValueError):
        return None


def recalc_meal_totals(meal):
    meal.total_calories = sum(item.calories or 0 for item in meal.items)

    meal.total_protein = sum(item.protein or 0 for item in meal.items)

    meal.total_fat = sum(item.fat or 0 for item in meal.items)

    meal.total_carbs = sum(item.carbs or 0 for item in meal.items)


def add_meal_service(user_id, data):
    meal = Meal(
        user_id=user_id,
        date=data.get("date") or date.today(),
        time=_parse_time(data.get("time")),
        name=data["name"],
        category=data["category"],
    )

    db.session.add(meal)
    db.session.commit()

    return meal


def update_meal_service(user_id, meal_id, data):
    meal = Meal.query.filter_by(
        id=meal_id,
        user_id=user_id,
    ).first()

    if meal is None:
        return None

    if "name" in data:
        name = (data["name"] or "").strip()

        if name:
            meal.name = name

    if "category" in data:
        category = (data["category"] or "").strip()

        if category:
            meal.category = category

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
    meal = Meal.query.filter_by(
        id=meal_id,
        user_id=user_id,
    ).first()

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
        total_calories=0,
        total_protein=0,
        total_fat=0,
        total_carbs=0,
    )

    db.session.add(new_meal)
    db.session.flush()

    for source_item in source_meal.items:
        from myapp.app.models import MealItem

        new_item = MealItem(
            meal_id=new_meal.id,
            name=source_item.name,
            weight=source_item.weight,
            calories=source_item.calories,
            protein=source_item.protein,
            fat=source_item.fat,
            carbs=source_item.carbs,
            fiber=source_item.fiber,
            category_id=source_item.category_id,
        )

        db.session.add(new_item)

    db.session.flush()

    recalc_meal_totals(new_meal)

    db.session.commit()

    return new_meal
