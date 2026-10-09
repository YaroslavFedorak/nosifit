from backend.app.utils.validation import as_db_id
from backend.app.extensions import db
from backend.app.models import Meal, MealItem, Product
from backend.app.services.nutrition.calculation_service import (
    NutritionValidationError,
    basis_product,
    calculate_product_nutrition,
    normalize_unit,
    product_basis,
)
from backend.app.services.nutrition.meal_service import recalc_meal_totals
from sqlalchemy import and_, or_
from sqlalchemy.orm import selectinload
from backend.app.services.nutrition.product_service import (
    get_product_name,
)
from backend.app.repositories.product_repository import (
    get_product_for_user,
)


def _get_meal(user_id, meal_id):
    meal_id = as_db_id(meal_id)
    if meal_id is None:
        return None
    return Meal.query.filter_by(
        id=meal_id,
        user_id=user_id,
    ).first()


def _apply_nutrition(item, nutrition):
    item.weight = nutrition.grams
    item.calories = int(nutrition.calories)
    item.protein = nutrition.protein
    item.fat = nutrition.fat
    item.carbs = nutrition.carbs
    item.fiber = nutrition.fiber
    item.sugar = nutrition.sugar
    item.saturated_fat = nutrition.saturated_fat
    item.salt = nutrition.salt
    item.liquid_ml = nutrition.liquid_ml


def build_entry(meal, product, amount, unit=None, locale="uk", dish=None):
    """A new entry with a snapshot of ``product``'s values at this moment."""
    unit = normalize_unit(unit, product.default_unit)
    nutrition = calculate_product_nutrition(product, amount, unit)

    item = MealItem(
        meal=meal,
        product_id=product.id,
        name=get_product_name(product, locale),
        amount=float(amount),
        unit=unit,
        basis=product_basis(product),
        dish_id=dish.id if dish is not None else None,
        dish_name=dish.name if dish is not None else None,
    )
    _apply_nutrition(item, nutrition)
    return item


def load_products_for_user(user_id, product_ids):
    """Products the user may log, by id, in one query.

    Catalog products must be active. The user's own products may be archived:
    a saved dish keeps working after one of its products is deleted.
    """
    ids = {as_db_id(product_id) for product_id in product_ids}
    if None in ids:
        raise NutritionValidationError("Product id is required")

    products = (
        Product.query
        .options(selectinload(Product.names))
        .filter(
            Product.id.in_(ids),
            or_(
                and_(
                    Product.owner_user_id.is_(None),
                    Product.is_active.is_(True),
                ),
                Product.owner_user_id == user_id,
            ),
        )
        .all()
    )
    products_by_id = {product.id: product for product in products}

    if len(products_by_id) != len(ids):
        raise NutritionValidationError("One or more products were not found")

    return products_by_id


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

    item = build_entry(
        meal,
        product,
        data.get("amount"),
        data.get("unit"),
        data.get("locale", "uk"),
    )

    db.session.add(item)
    db.session.flush()

    recalc_meal_totals(meal)
    db.session.commit()

    return item


def add_entries(user_id, meal, items, dish=None, products_by_id=None):
    """Add ``items`` ({product_id, amount, unit, locale}) to ``meal``; no commit.

    ``products_by_id`` skips the product query when the caller already
    loaded and checked them.
    """
    if products_by_id is None:
        products_by_id = load_products_for_user(
            user_id,
            [item.get("product_id") for item in items],
        )

    created_items = []
    for data in items:
        product = products_by_id[as_db_id(data.get("product_id"))]
        item = build_entry(
            meal,
            product,
            data.get("amount"),
            data.get("unit"),
            data.get("locale", "uk"),
            dish=dish,
        )
        db.session.add(item)
        created_items.append(item)

    db.session.flush()
    recalc_meal_totals(meal)
    return created_items


def add_items_service(user_id, meal_id, items):
    meal = _get_meal(user_id, meal_id)

    if meal is None:
        return None

    if not items:
        return []

    created_items = add_entries(user_id, meal, items)
    db.session.commit()

    return created_items


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

    if "product_id" in data:
        product = get_product_for_user(
            user_id,
            data.get("product_id"),
        )

        if product is None:
            raise NutritionValidationError("Product not found")

        # A different product is a new snapshot.
        item.product_id = product.id
        item.basis = product_basis(product)
        item.name = get_product_name(product, data.get("locale", "uk"))

    if "amount" in data or "unit" in data or "product_id" in data:
        # Rescale from the entry's own snapshot, so a product edited since
        # (or archived) does not change what was eaten. Entries logged before
        # snapshots existed fall back to the product once and get a snapshot.
        if item.basis is not None:
            source = basis_product(item.basis)
        elif item.product is not None:
            source = item.product
            item.basis = product_basis(item.product)
        else:
            raise NutritionValidationError("This entry cannot be recalculated")

        amount = data.get("amount") if "amount" in data else item.amount
        unit = normalize_unit(
            data.get("unit") if "unit" in data else item.unit,
            source.default_unit,
        )
        nutrition = calculate_product_nutrition(source, amount, unit)

        item.amount = float(amount)
        item.unit = unit
        _apply_nutrition(item, nutrition)

    if target_meal.id != old_meal.id:
        item.meal = target_meal
        db.session.flush()
        db.session.expire(old_meal, ["items"])

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
