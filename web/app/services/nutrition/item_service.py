from web.app import db
from web.app.models import Meal, MealItem

from web.app.services.nutrition.meal_service import (
    recalc_meal_totals,
)


def _parse_float(value, default=0):
    if value in (None, ""):
        return default

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def add_item_service(user_id, data):
    meal = Meal.query.filter_by(
        id=data["meal_id"],
        user_id=user_id,
    ).first()

    if meal is None:
        return None

    item = MealItem(
        meal_id=meal.id,
        name=data["name"],
        weight=(
            float(data["weight"]) if data.get("weight") not in (None, "") else None
        ),
        calories=int(
            _parse_float(
                data.get("calories"),
                0,
            )
        ),
        protein=_parse_float(
            data.get("protein"),
            0,
        ),
        fat=_parse_float(
            data.get("fat"),
            0,
        ),
        carbs=_parse_float(
            data.get("carbs"),
            0,
        ),
        fiber=_parse_float(
            data.get("fiber"),
            0,
        ),
        category_id=data.get("category_id"),
    )

    db.session.add(item)
    db.session.flush()

    recalc_meal_totals(meal)

    db.session.commit()

    return item


def update_item_service(user_id, item_id, data):
    item = (
        MealItem.query.join(Meal)
        .filter(
            MealItem.id == item_id,
            Meal.user_id == user_id,
        )
        .first()
    )

    if item is None:
        return None

    if "name" in data:
        name = (data["name"] or "").strip()

        if name:
            item.name = name

    if "weight" in data:
        item.weight = (
            float(data["weight"]) if data["weight"] not in (None, "") else None
        )

    if "calories" in data:
        item.calories = int(
            _parse_float(
                data["calories"],
                0,
            )
        )

    if "protein" in data:
        item.protein = _parse_float(
            data["protein"],
            0,
        )

    if "fat" in data:
        item.fat = _parse_float(
            data["fat"],
            0,
        )

    if "carbs" in data:
        item.carbs = _parse_float(
            data["carbs"],
            0,
        )

    if "fiber" in data:
        item.fiber = _parse_float(
            data["fiber"],
            0,
        )

    if "category_id" in data:
        item.category_id = data["category_id"]

    recalc_meal_totals(item.meal)

    db.session.commit()

    return item


def delete_item_service(user_id, item_id):
    item = (
        MealItem.query.join(Meal)
        .filter(
            MealItem.id == item_id,
            Meal.user_id == user_id,
        )
        .first()
    )

    if item is None:
        return False

    meal = item.meal

    db.session.delete(item)
    db.session.flush()

    recalc_meal_totals(meal)

    db.session.commit()

    return True
