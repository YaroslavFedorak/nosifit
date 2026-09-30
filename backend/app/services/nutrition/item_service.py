from backend.app.extensions import db
from backend.app.models import Meal, MealItem
from backend.app.services.nutrition.calculation_service import (
    NutritionValidationError,
    calculate_product_nutrition,
    normalize_unit,
)
from backend.app.services.nutrition.meal_service import recalc_meal_totals
from backend.app.services.nutrition.product_service import (
    get_product_name,
)
from backend.app.repositories.product_repository import (
    get_product_for_user,
)


def _get_meal(user_id, meal_id):
    return Meal.query.filter_by(
        id=meal_id,
        user_id=user_id,
    ).first()


def add_item_service(user_id, data):
    meal = _get_meal(user_id, data.get("meal_id"))

    if meal is None:
        return None

    product = get_product_for_user(
        user_id,
        data.get("product_id"),
    )

    if product is None:
        raise NutritionValidationError("Product not found")

    unit = normalize_unit(
        data.get("unit"),
        product.default_unit,
    )

    nutrition = calculate_product_nutrition(
        product,
        data.get("amount"),
        unit,
    )

    item = MealItem(
        meal_id=meal.id,
        product_id=product.id,
        name=get_product_name(
            product,
            data.get("locale", "uk"),
        ),
        amount=float(data["amount"]),
        unit=unit,
        weight=nutrition.grams,
        calories=int(nutrition.calories),
        protein=nutrition.protein,
        fat=nutrition.fat,
        carbs=nutrition.carbs,
        fiber=nutrition.fiber,
    )

    db.session.add(item)
    db.session.flush()

    recalc_meal_totals(meal)
    db.session.commit()

    return item


def update_item_service(user_id, item_id, data):
    item = (
        MealItem.query
        .join(Meal)
        .filter(
            MealItem.id == item_id,
            Meal.user_id == user_id,
        )
        .first()
    )

    if item is None:
        return None

    old_meal = item.meal
    target_meal = old_meal

    if "meal_id" in data:
        target_meal = _get_meal(user_id, data.get("meal_id"))

        if target_meal is None:
            raise NutritionValidationError("Target meal not found")

    product = item.product

    if "product_id" in data:
        product = get_product_for_user(
            user_id,
            data.get("product_id"),
        )

        if product is None:
            raise NutritionValidationError("Product not found")

        item.product_id = product.id

    if product is not None and (
        "amount" in data
        or "unit" in data
        or "product_id" in data
    ):
        amount = (
            data.get("amount")
            if "amount" in data
            else item.amount
        )

        unit = normalize_unit(
            data.get("unit") if "unit" in data else item.unit,
            product.default_unit,
        )

        nutrition = calculate_product_nutrition(
            product,
            amount,
            unit,
        )

        item.amount = float(amount)
        item.unit = unit
        item.weight = nutrition.grams
        item.name = get_product_name(
            product,
            data.get("locale", "uk"),
        )
        item.calories = int(nutrition.calories)
        item.protein = nutrition.protein
        item.fat = nutrition.fat
        item.carbs = nutrition.carbs
        item.fiber = nutrition.fiber

    if target_meal.id != old_meal.id:
        item.meal_id = target_meal.id

    recalc_meal_totals(old_meal)

    if target_meal.id != old_meal.id:
        recalc_meal_totals(target_meal)

    db.session.commit()

    return item


def delete_item_service(user_id, item_id):
    item = (
        MealItem.query
        .join(Meal)
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
