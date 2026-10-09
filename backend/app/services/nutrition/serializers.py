from backend.app.services.nutrition.calculation_service import partial_totals
from backend.app.services.nutrition.meal_categories import normalize_meal_category
from backend.app.services.nutrition.product_service import (
    get_product_name,
)


def _entry_name(item, locale):
    # Catalog products follow the interface language. A user's own product
    # keeps the name it had when it was logged, like its values.
    product = item.product
    if product is not None and product.owner_user_id is None:
        return get_product_name(product, locale)
    return item.name


def serialize_entry(item, locale="uk"):
    return {
        "id": item.id,
        "product_id": item.product_id,
        "name": _entry_name(item, locale),
        "amount": item.amount,
        "unit": item.unit,
        "weight": item.weight,
        "calories": item.calories,
        "protein": item.protein,
        "fat": item.fat,
        "carbs": item.carbs,
        "fiber": item.fiber,
        "sugar": item.sugar,
        "saturated_fat": item.saturated_fat,
        "salt": item.salt,
        "liquid_ml": item.liquid_ml,
        "dish_id": item.dish_id,
        "dish_name": item.dish_name,
    }


def serialize_meal(meal, locale="uk"):
    category = normalize_meal_category(meal.category) or meal.category
    items = list(meal.items)
    fiber, fiber_complete = partial_totals(items, "fiber")
    sugar, sugar_complete = partial_totals(items, "sugar")

    return {
        "id": meal.id,
        "name": category,
        "category": category,
        "date": meal.date.isoformat() if meal.date else None,
        "time": meal.time.strftime("%H:%M") if meal.time else None,
        "total_calories": meal.total_calories,
        "total_protein": meal.total_protein,
        "total_fat": meal.total_fat,
        "total_carbs": meal.total_carbs,
        "total_fiber": fiber,
        "total_sugar": sugar,
        "fiber_complete": fiber_complete,
        "sugar_complete": sugar_complete,
        "items": [serialize_entry(item, locale) for item in items],
    }
