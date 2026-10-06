from __future__ import annotations

from sqlalchemy import func, or_
from sqlalchemy.orm import selectinload

from backend.app.extensions import db
from backend.app.models import Meal, MealItem, Product, ProductFavorite, ProductName
from backend.app.repositories.product_repository import (
    get_favorite_products,
    get_product_for_user,
    get_recent_products,
    get_user_product,
)


SUPPORTED_LOCALES = {"uk", "en", "pl", "ru"}
SUPPORTED_SOURCES = {"system", "user", "imported"}
SUPPORTED_UNITS = {"g", "ml", "pcs"}
PRODUCT_CATEGORIES = {
    "meat", "fish", "dairy", "eggs", "grains", "bread", "vegetables",
    "fruits", "legumes", "nuts", "oils", "sweets", "beverages", "other",
}


class ProductServiceError(ValueError):
    pass


def normalize_locale(locale: str | None) -> str:
    normalized = (locale or "uk").strip().lower().replace("_", "-")
    normalized = normalized.split("-")[0]
    return normalized if normalized in SUPPORTED_LOCALES else "uk"


def get_product_name(product, locale="uk") -> str:
    locale = normalize_locale(locale)
    names = {name.locale: name.name for name in product.names}

    return (
        names.get(locale)
        or names.get("en")
        or names.get("uk")
        or next(iter(names.values()), "Unnamed product")
    )


def serialize_product(
    product,
    user_id,
    locale="uk",
    favorite_ids: set[int] | None = None,
) -> dict:
    if favorite_ids is None:
        is_favorite = (
            ProductFavorite.query
            .filter_by(
                user_id=user_id,
                product_id=product.id,
            )
            .first()
            is not None
        )
    else:
        is_favorite = product.id in favorite_ids

    return {
        "id": product.id,
        "name": get_product_name(product, locale),
        "brand": product.brand,
        "category": product.category,
        "source": product.source,
        "barcode": product.barcode,
        "kcal_per_100g": round(product.kcal_per_100g, 2),
        "protein_per_100g": round(product.protein_per_100g, 2),
        "fat_per_100g": round(product.fat_per_100g, 2),
        "carbs_per_100g": round(product.carbs_per_100g, 2),
        "fiber_per_100g": round(product.fiber_per_100g, 2),
        "liquid_ml_per_100g": round(product.liquid_ml_per_100g, 2),
        "default_unit": product.default_unit,
        "grams_per_unit": product.grams_per_unit,
        "is_favorite": is_favorite,
        # The user's own products can be edited and deleted.
        "is_own": product.owner_user_id is not None and product.owner_user_id == user_id,
    }


def serialize_product_list(products, user_id, locale="uk"):
    if not products:
        return []

    favorite_ids = {
        product_id
        for (product_id,) in (
            ProductFavorite.query
            .with_entities(ProductFavorite.product_id)
            .filter(
                ProductFavorite.user_id == user_id,
                ProductFavorite.product_id.in_(
                    [product.id for product in products]
                ),
            )
            .all()
        )
    }

    return [
        serialize_product(
            product,
            user_id,
            locale,
            favorite_ids=favorite_ids,
        )
        for product in products
    ]


def search_products(
    user_id,
    query="",
    locale="uk",
    limit=20,
    category=None,
    offset=0,
):
    locale = normalize_locale(locale)
    query = (query or "").strip()
    category = (category or "").strip().lower() or None
    limit = min(max(int(limit), 1), 50)
    offset = max(int(offset), 0)

    product_query = (
        Product.query
        .options(selectinload(Product.names))
        .filter(
            Product.is_active.is_(True),
            or_(
                Product.owner_user_id.is_(None),
                Product.owner_user_id == user_id,
            ),
        )
    )

    if category:
        if category not in PRODUCT_CATEGORIES:
            return []
        product_query = product_query.filter(Product.category == category)

    if not query:
        return serialize_product_list(
            product_query
            .order_by(Product.source.desc(), Product.id.desc())
            .offset(offset)
            .limit(limit)
            .all(),
            user_id,
            locale,
        )

    # Match names in every language: people often type a product the way
    # they know it, regardless of the interface language. Results are still
    # displayed in the user's locale.
    name_filter = ProductName.locale.in_(SUPPORTED_LOCALES)
    exact_products = (
        product_query
        .join(ProductName)
        .filter(
            name_filter,
            or_(
                ProductName.name.ilike(f"%{query}%"),
                Product.brand.ilike(f"%{query}%"),
            ),
        )
        .distinct()
        .order_by(Product.source.desc(), Product.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    if exact_products:
        return serialize_product_list(exact_products, user_id, locale)

    similarity = func.greatest(
        func.word_similarity(query, ProductName.name),
        func.similarity(query, ProductName.name),
        func.similarity(query, func.coalesce(Product.brand, "")),
    )
    fuzzy_products = (
        product_query
        .join(ProductName)
        .filter(
            name_filter,
            similarity >= (0.30 if len(query) <= 3 else 0.35),
        )
        .group_by(Product.id)
        .order_by(
            func.max(similarity).desc(),
            Product.source.desc(),
            Product.id.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    return serialize_product_list(fuzzy_products, user_id, locale)


def get_product(user_id, product_id, locale="uk"):
    product = get_product_for_user(user_id, product_id)
    if product is None:
        return None

    return serialize_product(product, user_id, locale)


# Per-100 g sanity limits. Pure fat is ~900 kcal / 100 g, so anything above
# these values is a typo.
NUTRITION_LIMITS = {
    "kcal_per_100g": 950.0,
    "protein_per_100g": 100.0,
    "fat_per_100g": 100.0,
    "carbs_per_100g": 100.0,
    "fiber_per_100g": 100.0,
    "liquid_ml_per_100g": 100.0,
}

MAX_PRODUCT_NAME_LENGTH = 120
MAX_GRAMS_PER_UNIT = 5000.0


def _nutrition_value(data, key):
    raw = data.get(key, 0)
    if raw in (None, ""):
        raw = 0

    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ProductServiceError(f"Invalid {key}")

    if value != value or value < 0:
        raise ProductServiceError(f"{key} cannot be negative")

    limit = NUTRITION_LIMITS.get(key)
    if limit is not None and value > limit:
        raise ProductServiceError(f"{key} cannot be greater than {limit:g}")

    return value


def _grams_per_unit(value):
    try:
        grams_per_unit = float(value)
    except (TypeError, ValueError):
        raise ProductServiceError("Invalid grams_per_unit")

    if grams_per_unit != grams_per_unit or grams_per_unit <= 0:
        raise ProductServiceError("grams_per_unit must be positive")

    if grams_per_unit > MAX_GRAMS_PER_UNIT:
        raise ProductServiceError("grams_per_unit is too large")

    return grams_per_unit


MAX_BRAND_LENGTH = 120  # products.brand
MAX_BARCODE_LENGTH = 32  # products.barcode


def _text(data, key, max_length=None):
    """Optional text field: wrong types and over-long values are errors."""
    value = data.get(key)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ProductServiceError(f"{key} must be text")
    value = value.strip()
    if max_length is not None and len(value) > max_length:
        raise ProductServiceError(f"{key} is too long")
    return value


def create_user_product(user_id, data, locale="uk"):
    locale = normalize_locale(locale)
    name = _text(data, "name")

    if not name:
        raise ProductServiceError("Product name is required")

    if len(name) > MAX_PRODUCT_NAME_LENGTH:
        raise ProductServiceError("Product name is too long")

    unit = (_text(data, "default_unit") or "g").lower()
    if unit not in SUPPORTED_UNITS:
        raise ProductServiceError("Unsupported default unit")

    grams_per_unit = _grams_per_unit(data.get("grams_per_unit", 1))

    category = (_text(data, "category") or "other").lower()
    if category not in PRODUCT_CATEGORIES:
        raise ProductServiceError("Unsupported product category")

    product = Product(
        owner_user_id=user_id,
        source="user",
        brand=_text(data, "brand", MAX_BRAND_LENGTH) or None,
        # Barcodes are unique across all products; a user-chosen value could
        # collide with (and block) another user's product. Not used by the UI.
        barcode=None,
        kcal_per_100g=_nutrition_value(data, "kcal_per_100g"),
        protein_per_100g=_nutrition_value(data, "protein_per_100g"),
        fat_per_100g=_nutrition_value(data, "fat_per_100g"),
        carbs_per_100g=_nutrition_value(data, "carbs_per_100g"),
        fiber_per_100g=_nutrition_value(data, "fiber_per_100g"),
        liquid_ml_per_100g=_nutrition_value(data, "liquid_ml_per_100g"),
        category=category,
        default_unit=unit,
        grams_per_unit=grams_per_unit,
    )

    db.session.add(product)
    db.session.flush()

    db.session.add(
        ProductName(
            product_id=product.id,
            locale=locale,
            name=name,
        )
    )

    db.session.commit()
    return serialize_product(product, user_id, locale)


def _recalculate_product_entries(user_id, product, locale="uk"):
    """Re-apply the product's (corrected) values to everything already logged.

    Fixing a typo in a user's own product should fix the days it was used on,
    not only future entries.
    """
    from backend.app.services.nutrition.calculation_service import (
        NutritionValidationError,
        calculate_product_nutrition,
    )
    from backend.app.services.nutrition.meal_service import recalc_meal_totals

    items = (
        MealItem.query
        .join(Meal)
        .filter(
            MealItem.product_id == product.id,
            Meal.user_id == user_id,
        )
        .all()
    )

    meals = {}
    for item in items:
        try:
            nutrition = calculate_product_nutrition(
                product,
                item.amount if item.amount is not None else (item.weight or 100),
                item.unit or product.default_unit,
            )
        except NutritionValidationError:
            continue

        item.name = get_product_name(product, locale)
        item.weight = nutrition.grams
        item.calories = int(nutrition.calories)
        item.protein = nutrition.protein
        item.fat = nutrition.fat
        item.carbs = nutrition.carbs
        item.fiber = nutrition.fiber
        item.liquid_ml = nutrition.liquid_ml
        meals[item.meal_id] = item.meal

    db.session.flush()
    for meal in meals.values():
        recalc_meal_totals(meal)

    return len(items)


def update_user_product(user_id, product_id, data, locale="uk"):
    product = get_user_product(user_id, product_id)
    if product is None or not product.is_active:
        return None

    locale = normalize_locale(locale)

    if "name" in data:
        name = _text(data, "name")
        if not name:
            raise ProductServiceError("Product name cannot be empty")

        if len(name) > MAX_PRODUCT_NAME_LENGTH:
            raise ProductServiceError("Product name is too long")

        # A user's product has one name; keep every locale row in sync so a
        # language switch never brings the old (wrong) name back.
        names = ProductName.query.filter_by(product_id=product.id).all()
        for localized in names:
            localized.name = name

        if not any(localized.locale == locale for localized in names):
            db.session.add(
                ProductName(
                    product_id=product.id,
                    locale=locale,
                    name=name,
                )
            )

    for key in (
        "kcal_per_100g",
        "protein_per_100g",
        "fat_per_100g",
        "carbs_per_100g",
        "fiber_per_100g",
        "liquid_ml_per_100g",
    ):
        if key in data:
            setattr(product, key, _nutrition_value(data, key))

    if "brand" in data:
        product.brand = _text(data, "brand", MAX_BRAND_LENGTH) or None

    if "category" in data:
        category = (_text(data, "category") or "other").lower()
        if category not in PRODUCT_CATEGORIES:
            raise ProductServiceError("Unsupported product category")
        product.category = category

    if "default_unit" in data:
        unit = _text(data, "default_unit").lower()
        if unit not in SUPPORTED_UNITS:
            raise ProductServiceError("Unsupported default unit")
        product.default_unit = unit

    if "grams_per_unit" in data:
        grams_per_unit = _grams_per_unit(data["grams_per_unit"])

        product.grams_per_unit = grams_per_unit

    db.session.flush()
    db.session.expire(product, ["names"])
    _recalculate_product_entries(user_id, product, locale)

    db.session.commit()
    return serialize_product(product, user_id, locale)


def archive_user_product(user_id, product_id):
    product = get_user_product(user_id, product_id)
    if product is None:
        return False

    if not product.is_active:
        return False

    # Archived, not deleted: meals that already used it keep their history.
    product.is_active = False
    ProductFavorite.query.filter_by(product_id=product.id).delete()
    db.session.commit()
    return True


def set_favorite(user_id, product_id, favorite, locale="uk"):
    product = get_product_for_user(user_id, product_id)
    if product is None:
        return None

    entry = ProductFavorite.query.filter_by(
        user_id=user_id,
        product_id=product.id,
    ).first()

    if favorite and entry is None:
        db.session.add(
            ProductFavorite(
                user_id=user_id,
                product_id=product.id,
            )
        )
    elif not favorite and entry is not None:
        db.session.delete(entry)

    db.session.commit()
    return serialize_product(product, user_id, locale)


def get_recent(user_id, locale="uk", limit=12):
    return serialize_product_list(
        get_recent_products(user_id, limit),
        user_id,
        locale,
    )


def get_favorites(user_id, locale="uk", limit=50):
    return serialize_product_list(
        get_favorite_products(user_id, limit),
        user_id,
        locale,
    )


def get_user_products(user_id, locale="uk"):
    products = (
        Product.query
        .options(selectinload(Product.names))
        .filter_by(
            owner_user_id=user_id,
            source="user",
            is_active=True,
        )
        .order_by(Product.created_at.desc())
        .all()
    )

    return serialize_product_list(products, user_id, locale)
