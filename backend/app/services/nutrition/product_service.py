from __future__ import annotations

from sqlalchemy import func, or_
from sqlalchemy.orm import selectinload

from backend.app.extensions import db
from backend.app.models import Product, ProductFavorite, ProductName
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

    name_filter = ProductName.locale.in_({locale, "en", "uk"})
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
            similarity >= 0.35,
        )
        .distinct()
        .order_by(similarity.desc(), Product.source.desc(), Product.id.desc())
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


def _nutrition_value(data, key):
    try:
        value = float(data.get(key, 0))
    except (TypeError, ValueError):
        raise ProductServiceError(f"Invalid {key}")

    if value < 0:
        raise ProductServiceError(f"{key} cannot be negative")

    return value


def create_user_product(user_id, data, locale="uk"):
    locale = normalize_locale(locale)
    name = (data.get("name") or "").strip()

    if not name:
        raise ProductServiceError("Product name is required")

    unit = (data.get("default_unit") or "g").strip().lower()
    if unit not in SUPPORTED_UNITS:
        raise ProductServiceError("Unsupported default unit")

    try:
        grams_per_unit = float(data.get("grams_per_unit", 1))
    except (TypeError, ValueError):
        raise ProductServiceError("Invalid grams_per_unit")

    if grams_per_unit <= 0:
        raise ProductServiceError("grams_per_unit must be positive")

    category = (data.get("category") or "other").strip().lower()
    if category not in PRODUCT_CATEGORIES:
        raise ProductServiceError("Unsupported product category")

    product = Product(
        owner_user_id=user_id,
        source="user",
        brand=(data.get("brand") or "").strip() or None,
        barcode=(data.get("barcode") or "").strip() or None,
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


def update_user_product(user_id, product_id, data, locale="uk"):
    product = get_user_product(user_id, product_id)
    if product is None:
        return None

    locale = normalize_locale(locale)

    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            raise ProductServiceError("Product name cannot be empty")

        localized = ProductName.query.filter_by(
            product_id=product.id,
            locale=locale,
        ).first()

        if localized:
            localized.name = name
        else:
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
        product.brand = (data.get("brand") or "").strip() or None

    if "category" in data:
        category = (data.get("category") or "other").strip().lower()
        if category not in PRODUCT_CATEGORIES:
            raise ProductServiceError("Unsupported product category")
        product.category = category

    if "default_unit" in data:
        unit = (data.get("default_unit") or "").strip().lower()
        if unit not in SUPPORTED_UNITS:
            raise ProductServiceError("Unsupported default unit")
        product.default_unit = unit

    if "grams_per_unit" in data:
        try:
            grams_per_unit = float(data["grams_per_unit"])
        except (TypeError, ValueError):
            raise ProductServiceError("Invalid grams_per_unit")

        if grams_per_unit <= 0:
            raise ProductServiceError("grams_per_unit must be positive")

        product.grams_per_unit = grams_per_unit

    db.session.commit()
    return serialize_product(product, user_id, locale)


def archive_user_product(user_id, product_id):
    product = get_user_product(user_id, product_id)
    if product is None:
        return False

    product.is_active = False
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
