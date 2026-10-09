"""Reusable dishes ("Мої страви") and logging food in one operation.

A dish is a template: a name plus products with amounts. Logging a dish
copies its components into meal entries, each with its own nutrition
snapshot. The client may change the components for this one time (other
amounts, a product removed, replaced or added) by sending the final list;
the template is never touched by logging, and editing the template later
never touches what was logged.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time

from sqlalchemy.orm import selectinload

from backend.app.extensions import db
from backend.app.models import Dish, DishItem, Meal, Product
from backend.app.services.nutrition.calculation_service import (
    NutritionValidationError,
    calculate_product_nutrition,
    normalize_amount,
    normalize_unit,
    partial_sum,
    validate_amount_for_unit,
)
from backend.app.services.nutrition.item_service import add_entries, load_products_for_user
from backend.app.services.nutrition.meal_categories import normalize_meal_category
from backend.app.services.nutrition.product_service import get_product_name, normalize_locale
from backend.app.utils.name_normalization import normalize_name
from backend.app.utils.validation import as_db_id


MAX_DISH_NAME_LENGTH = 120
MAX_DISH_ITEMS = 30
MAX_LOG_ITEMS = 50
DISH_SORTS = ("recent", "popular", "name")


class DishServiceError(ValueError):
    def __init__(self, message, code="invalid_dish", status=400):
        super().__init__(message)
        self.code = code
        self.status = status


def _dish_query(user_id):
    return Dish.query.options(
        selectinload(Dish.items)
        .selectinload(DishItem.product)
        .selectinload(Product.names)
    ).filter(Dish.user_id == user_id)


def get_user_dish(user_id, dish_id):
    dish_id = as_db_id(dish_id)
    if dish_id is None:
        return None
    return _dish_query(user_id).filter(Dish.id == dish_id).first()


# --- serialization -------------------------------------------------------

def _component(item, locale):
    product = item.product
    nutrition = calculate_product_nutrition(product, item.amount, item.unit)
    return {
        "product_id": product.id,
        "name": get_product_name(product, locale),
        "amount": item.amount,
        "unit": item.unit,
        "default_unit": product.default_unit,
        "grams_per_unit": product.grams_per_unit,
        "grams": nutrition.grams,
        "calories": nutrition.calories,
        "protein": nutrition.protein,
        "fat": nutrition.fat,
        "carbs": nutrition.carbs,
        "fiber": nutrition.fiber,
        "sugar": nutrition.sugar,
        # Per-100 g values let a client rescale a component it edits for one
        # meal without another request.
        "kcal_per_100g": product.kcal_per_100g,
        "protein_per_100g": product.protein_per_100g,
        "fat_per_100g": product.fat_per_100g,
        "carbs_per_100g": product.carbs_per_100g,
        "fiber_per_100g": product.fiber_per_100g,
        "sugar_per_100g": product.sugar_per_100g,
        # False when the user has deleted their product since: the dish
        # still works, the client may suggest replacing it.
        "is_active": bool(product.is_active),
    }


def serialize_dish(dish, locale="uk"):
    locale = normalize_locale(locale)
    components = [_component(item, locale) for item in dish.items]

    fiber, fiber_complete = partial_sum(c["fiber"] for c in components)
    sugar, sugar_complete = partial_sum(c["sugar"] for c in components)

    return {
        "id": dish.id,
        "name": dish.name,
        "use_count": dish.use_count,
        "last_used_at": dish.last_used_at.isoformat() if dish.last_used_at else None,
        "items": components,
        "totals": {
            "grams": round(sum(c["grams"] for c in components), 1),
            "calories": round(sum(c["calories"] for c in components)),
            "protein": round(sum(c["protein"] for c in components), 1),
            "fat": round(sum(c["fat"] for c in components), 1),
            "carbs": round(sum(c["carbs"] for c in components), 1),
            "fiber": None if fiber is None else round(fiber, 1),
            "fiber_complete": fiber_complete,
            "sugar": None if sugar is None else round(sugar, 1),
            "sugar_complete": sugar_complete,
        },
    }


# --- validation ----------------------------------------------------------

def _dish_name(data):
    name = data.get("name")
    if not isinstance(name, str) or not " ".join(name.split()):
        raise DishServiceError("Dish name is required")
    name = " ".join(name.split())
    if len(name) > MAX_DISH_NAME_LENGTH:
        raise DishServiceError("Dish name is too long")
    normalized = normalize_name(name)
    if not normalized:
        raise DishServiceError("Dish name must contain letters or digits")
    return name, normalized


def _clean_items(raw_items, max_items):
    """Validated ``[{product_id, amount, unit}]``; repeated products merged."""
    if not isinstance(raw_items, list) or not raw_items:
        raise DishServiceError("items must be a non-empty list", "invalid_entry")
    if len(raw_items) > max_items:
        raise DishServiceError(f"At most {max_items} items", "invalid_entry")

    merged: dict[int, dict] = {}
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise DishServiceError("Each item must be an object", "invalid_entry")
        product_id = as_db_id(raw.get("product_id"))
        if product_id is None:
            raise DishServiceError("Product id is required", "invalid_entry")
        try:
            amount = normalize_amount(raw.get("amount"))
            unit = normalize_unit(raw.get("unit")) if raw.get("unit") else None
        except NutritionValidationError as exc:
            raise DishServiceError(str(exc), "invalid_entry")

        existing = merged.get(product_id)
        if existing is None:
            merged[product_id] = {"product_id": product_id, "amount": amount, "unit": unit}
        elif existing["unit"] == unit:
            existing["amount"] += amount
        else:
            raise DishServiceError(
                "The same product is listed twice with different units",
                "invalid_entry",
            )
    return list(merged.values())


def _resolve_items(user_id, items, known=None):
    """Attach products (one query) and check amounts against their units.

    ``known`` maps ids to products already loaded and checked (the components
    of the user's own dish); only the others are queried.
    """
    products = dict(known or {})
    missing = [item["product_id"] for item in items if item["product_id"] not in products]
    if missing:
        try:
            products.update(load_products_for_user(user_id, missing))
        except NutritionValidationError as exc:
            raise DishServiceError(str(exc), "product_not_found", 404)

    for item in items:
        product = products[item["product_id"]]
        item["unit"] = normalize_unit(item["unit"], product.default_unit)
        try:
            validate_amount_for_unit(item["amount"], item["unit"])
        except NutritionValidationError as exc:
            raise DishServiceError(str(exc), "invalid_entry")
        item["product"] = product
    return items


def _ensure_unique_name(user_id, normalized, exclude_id=None):
    query = Dish.query.filter(
        Dish.user_id == user_id,
        Dish.normalized_name == normalized,
    )
    if exclude_id is not None:
        query = query.filter(Dish.id != exclude_id)
    if db.session.query(query.exists()).scalar():
        raise DishServiceError(
            "You already have a dish with this name",
            "duplicate_dish",
            409,
        )


def _replace_items(dish, items):
    # Flush the removals first: the (dish_id, product_id) unique constraint
    # would otherwise reject a product that stays in the dish.
    dish.items.clear()
    db.session.flush()
    for position, item in enumerate(items):
        dish.items.append(
            DishItem(
                product=item["product"],
                product_id=item["product"].id,
                amount=round(item["amount"], 2),
                unit=item["unit"],
                position=position,
            )
        )


# --- CRUD ------------------------------------------------------------------

def list_dishes(user_id, locale="uk", query="", sort="recent", limit=20, offset=0):
    """``(dishes, has_more)``; ``query`` matches the name (prefix or substring)."""
    sort = sort if sort in DISH_SORTS else "recent"
    limit = min(max(int(limit), 1), 50)
    offset = max(int(offset), 0)

    dish_query = _dish_query(user_id)
    normalized = normalize_name(query)
    if normalized:
        escaped = normalized.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        dish_query = dish_query.filter(
            Dish.normalized_name.like(f"%{escaped}%", escape="\\")
        )

    if sort == "popular":
        order = (Dish.use_count.desc(), Dish.last_used_at.desc().nullslast(), Dish.id.desc())
    elif sort == "name":
        order = (Dish.normalized_name.asc(), Dish.id.asc())
    else:
        order = (Dish.last_used_at.desc().nullslast(), Dish.created_at.desc(), Dish.id.desc())

    dishes = dish_query.order_by(*order).offset(offset).limit(limit + 1).all()
    has_more = len(dishes) > limit
    return [serialize_dish(dish, locale) for dish in dishes[:limit]], has_more


def create_dish(user_id, data, locale="uk"):
    name, normalized = _dish_name(data)
    items = _resolve_items(user_id, _clean_items(data.get("items"), MAX_DISH_ITEMS))
    _ensure_unique_name(user_id, normalized)

    dish = Dish(user_id=user_id, name=name, normalized_name=normalized, use_count=0)
    db.session.add(dish)
    db.session.flush()
    _replace_items(dish, items)
    db.session.commit()
    return serialize_dish(dish, locale)


def update_dish(user_id, dish_id, data, locale="uk"):
    """Rename and/or replace the whole component list atomically."""
    dish = get_user_dish(user_id, dish_id)
    if dish is None:
        return None

    if "name" in data:
        name, normalized = _dish_name(data)
        _ensure_unique_name(user_id, normalized, exclude_id=dish.id)
        dish.name = name
        dish.normalized_name = normalized

    if "items" in data:
        items = _resolve_items(user_id, _clean_items(data.get("items"), MAX_DISH_ITEMS))
        _replace_items(dish, items)

    dish.updated_at = datetime.utcnow()
    db.session.commit()
    return serialize_dish(dish, locale)


def delete_dish(user_id, dish_id):
    dish_id = as_db_id(dish_id)
    if dish_id is None:
        return False
    dish = Dish.query.filter_by(id=dish_id, user_id=user_id).first()
    if dish is None:
        return False
    # Logged entries keep their snapshot; their dish_id becomes NULL.
    db.session.delete(dish)
    db.session.commit()
    return True


# --- logging ---------------------------------------------------------------

def _parse_date(value):
    if value in (None, ""):
        return date.today()
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        raise DishServiceError("Invalid date", "invalid_entry")


def _parse_time(value):
    if value in (None, ""):
        return None
    try:
        return datetime.strptime(str(value), "%H:%M").time()
    except ValueError:
        raise DishServiceError("Invalid time", "invalid_entry")


def _meal_for(user_id, day: date, category: str, at: time | None):
    """The user's meal of this category on this day, created if missing."""
    meal = (
        Meal.query
        .options(selectinload(Meal.items))
        .filter_by(user_id=user_id, date=day, category=category)
        .order_by(Meal.id.asc())
        .first()
    )
    if meal is None:
        meal = Meal(
            user_id=user_id,
            date=day,
            time=at,
            name=category,
            category=category,
            items=[],  # known empty: no lazy load when totals are counted
        )
        db.session.add(meal)
        db.session.flush()
    elif meal.time is None and at is not None:
        meal.time = at
    return meal


@dataclass(frozen=True)
class LoggedFood:
    meal: Meal
    meal_id: int
    date: date
    entry_ids: list[int]


def log_food(user_id, data):
    """Add products, or a dish (possibly adjusted), to a meal in one call.

    ``data``: ``category`` (required), ``date`` (default today), ``time``,
    ``dish_id`` and/or ``items`` ([{product_id, amount, unit}]). With a dish
    and no ``items`` the dish is logged as saved; with ``items`` those are
    logged as this time's version of the dish. Returns a ``LoggedFood``.

    One transaction; the ids are read before the commit so the caller does
    not reload every expired entry (an N+1 on large dishes).
    """
    category = normalize_meal_category(data.get("category"))
    if category is None:
        raise DishServiceError("Unknown meal category", "invalid_category")

    day = _parse_date(data.get("date"))
    at = _parse_time(data.get("time"))
    locale = normalize_locale(data.get("locale"))

    dish = None
    if data.get("dish_id") is not None:
        dish = get_user_dish(user_id, data.get("dish_id"))
        if dish is None:
            raise DishServiceError("Dish not found", "dish_not_found", 404)

    raw_items = data.get("items")
    if raw_items is None and dish is not None:
        raw_items = [
            {"product_id": item.product_id, "amount": item.amount, "unit": item.unit}
            for item in dish.items
        ]
    # Everything is checked before the meal is touched: unknown or foreign
    # products (404), amounts over the unit limits (400).
    # The dish's own components come loaded with it; only products added for
    # this meal are queried.
    known = {item.product_id: item.product for item in dish.items} if dish else None
    items = _resolve_items(user_id, _clean_items(raw_items, MAX_LOG_ITEMS), known)
    products_by_id = {item["product"].id: item["product"] for item in items}
    for item in items:
        item["locale"] = locale

    meal = _meal_for(user_id, day, category, at)
    try:
        entries = add_entries(
            user_id, meal, items, dish=dish, products_by_id=products_by_id
        )
    except NutritionValidationError as exc:
        db.session.rollback()
        raise DishServiceError(str(exc), "invalid_entry")

    if dish is not None:
        dish.use_count = (dish.use_count or 0) + 1
        dish.last_used_at = datetime.utcnow()

    db.session.flush()
    result = LoggedFood(
        meal=meal,
        meal_id=meal.id,
        date=meal.date,
        entry_ids=[entry.id for entry in entries],
    )
    db.session.commit()
    return result
