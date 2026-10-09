from __future__ import annotations

from sqlalchemy import case, func, or_, text
from sqlalchemy.orm import selectinload

from backend.app.extensions import db
from backend.app.models import Product, ProductFavorite, ProductName
from backend.app.repositories.product_repository import (
    get_favorite_products,
    get_product_for_user,
    get_recent_products,
    get_user_product,
)
from backend.app.utils.name_normalization import normalize_name


SUPPORTED_LOCALES = {"uk", "en", "pl", "ru"}
SUPPORTED_SOURCES = {"system", "user", "imported"}
SUPPORTED_UNITS = {"g", "ml", "pcs"}
PRODUCT_CATEGORIES = {
    "meat", "poultry", "fish", "seafood", "eggs", "dairy", "cheese",
    "grains", "pasta", "bread", "legumes", "vegetables", "fruits", "berries",
    "nuts", "seeds", "oils", "sauces", "prepared", "fast_food", "sweets",
    "snacks", "beverages", "ingredients", "other",
}


class ProductServiceError(ValueError):
    def __init__(self, message, code="invalid_product"):
        super().__init__(message)
        self.code = code


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


def _round(value, digits=2):
    return None if value is None else round(value, digits)


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
        # Every value is per 100 g; ``ml`` and ``pcs`` convert through
        # ``grams_per_unit``. None = unknown (shown as "—"), not 0.
        "kcal_per_100g": round(product.kcal_per_100g, 2),
        "protein_per_100g": round(product.protein_per_100g, 2),
        "fat_per_100g": round(product.fat_per_100g, 2),
        "carbs_per_100g": round(product.carbs_per_100g, 2),
        "fiber_per_100g": _round(product.fiber_per_100g),
        "sugar_per_100g": _round(product.sugar_per_100g),
        "saturated_fat_per_100g": _round(product.saturated_fat_per_100g),
        "salt_per_100g": _round(product.salt_per_100g, 3),
        "liquid_ml_per_100g": round(product.liquid_ml_per_100g, 2),
        "default_unit": product.default_unit,
        "grams_per_unit": product.grams_per_unit,
        "data_source": product.data_source,
        "source_ref": product.source_ref,
        "verified": bool(product.verified),
        "is_favorite": is_favorite,
        # The user's own products can be edited and deleted.
        "is_own": product.owner_user_id is not None and product.owner_user_id == user_id,
        "is_active": bool(product.is_active),
    }


def favorite_ids_for(user_id, product_ids) -> set[int]:
    if not product_ids:
        return set()
    return {
        product_id
        for (product_id,) in (
            ProductFavorite.query
            .with_entities(ProductFavorite.product_id)
            .filter(
                ProductFavorite.user_id == user_id,
                ProductFavorite.product_id.in_(list(product_ids)),
            )
            .all()
        )
    }


def serialize_product_list(products, user_id, locale="uk"):
    if not products:
        return []

    favorite_ids = favorite_ids_for(user_id, [product.id for product in products])

    return [
        serialize_product(
            product,
            user_id,
            locale,
            favorite_ids=favorite_ids,
        )
        for product in products
    ]


# --- search -----------------------------------------------------------------

# Typo-tolerant fallback threshold for pg_trgm word similarity (0..1).
FUZZY_THRESHOLD = 0.4
MAX_QUERY_LENGTH = 80


def _visible_products(user_id):
    return Product.query.filter(
        Product.is_active.is_(True),
        or_(
            Product.owner_user_id.is_(None),
            Product.owner_user_id == user_id,
        ),
    )


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _load_in_order(product_ids):
    if not product_ids:
        return []
    products = (
        Product.query
        .options(selectinload(Product.names))
        .filter(Product.id.in_(product_ids))
        .all()
    )
    by_id = {product.id: product for product in products}
    return [by_id[product_id] for product_id in product_ids if product_id in by_id]


def _ranked_match_ids(user_id, normalized, raw_query, category, limit, offset):
    """Ids of products whose name contains every query word, best first.

    Rank: exact name, name starts with the query, a word starts with the
    query, then any position. Own products come before the catalog at the
    same rank, shorter (more generic) names before longer ones. Every
    locale is searched; the GIN trigram index serves the ``LIKE '%…%'``.
    """
    name = ProductName.normalized_name
    escaped = _escape_like(normalized)

    rank = case(
        (name == normalized, 0),
        (name.like(f"{escaped}%", escape="\\"), 1),
        (name.like(f"% {escaped}%", escape="\\"), 2),
        else_=3,
    )

    word_filters = [
        name.like(f"%{_escape_like(word)}%", escape="\\")
        for word in normalized.split()
    ]
    brand_filter = Product.brand.ilike(f"%{_escape_like(raw_query)}%", escape="\\")

    query = (
        _visible_products(user_id)
        .join(ProductName, ProductName.product_id == Product.id)
        .filter(or_(db.and_(*word_filters), brand_filter))
    )
    if category:
        query = query.filter(Product.category == category)

    rows = (
        query
        .with_entities(Product.id)
        .group_by(Product.id)
        .order_by(
            func.min(rank),
            func.bool_or(Product.owner_user_id.is_not(None)).desc(),
            func.min(func.length(name)),
            Product.id,
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [row[0] for row in rows]


def _fuzzy_match_ids(user_id, normalized, category, limit, offset):
    """Typo-tolerant fallback ("куряче фле" → "куряче філе").

    Runs only when the exact word match finds nothing, so a normal search
    costs one query. ``<%`` (word similarity) can use the trigram index.
    """
    db.session.execute(
        text("SELECT set_config('pg_trgm.word_similarity_threshold', :t, true)"),
        {"t": str(FUZZY_THRESHOLD)},
    )
    name = ProductName.normalized_name
    score = func.word_similarity(normalized, name)

    query = (
        _visible_products(user_id)
        .join(ProductName, ProductName.product_id == Product.id)
        .filter(name.op("%>")(normalized))
    )
    if category:
        query = query.filter(Product.category == category)

    rows = (
        query
        .with_entities(Product.id)
        .group_by(Product.id)
        .order_by(
            # Best matching words plus whole-name closeness: "куряче фле"
            # ranks "Куряче філе" above "Яйце куряче", "грчка" ranks
            # "Гречка" above "Борошно гречане".
            func.max(score + func.similarity(normalized, name)).desc(),
            Product.id,
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [row[0] for row in rows]


def search_products_page(
    user_id,
    query="",
    locale="uk",
    limit=20,
    category=None,
    offset=0,
):
    """``(products, has_more)`` for one page of search results."""
    locale = normalize_locale(locale)
    raw_query = (query or "").strip()[:MAX_QUERY_LENGTH]
    normalized = normalize_name(raw_query)
    category = (category or "").strip().lower() or None
    limit = min(max(int(limit), 1), 50)
    offset = max(int(offset), 0)

    if category and category not in PRODUCT_CATEGORIES:
        return [], False

    # One extra row tells whether there is a next page.
    if not normalized:
        product_query = _visible_products(user_id).options(selectinload(Product.names))
        if category:
            product_query = product_query.filter(Product.category == category)
        products = (
            product_query
            .order_by(Product.source.desc(), Product.id.desc())
            .offset(offset)
            .limit(limit + 1)
            .all()
        )
    else:
        ids = _ranked_match_ids(user_id, normalized, raw_query, category, limit + 1, offset)
        # Fuzzy results only when the exact list is empty altogether (on a
        # later page that needs one cheap check), never mixed into it.
        if not ids and (
            offset == 0
            or not _ranked_match_ids(user_id, normalized, raw_query, category, 1, 0)
        ):
            ids = _fuzzy_match_ids(user_id, normalized, category, limit + 1, offset)
        products = _load_in_order(ids)

    has_more = len(products) > limit
    return serialize_product_list(products[:limit], user_id, locale), has_more


def search_products(
    user_id,
    query="",
    locale="uk",
    limit=20,
    category=None,
    offset=0,
):
    products, _ = search_products_page(user_id, query, locale, limit, category, offset)
    return products


def get_product(user_id, product_id, locale="uk"):
    product = get_product_for_user(user_id, product_id)
    if product is None:
        return None

    return serialize_product(product, user_id, locale)


# --- user products ----------------------------------------------------------

# Per-100 g sanity limits. Pure fat is ~900 kcal / 100 g, so anything above
# these values is a typo.
NUTRITION_LIMITS = {
    "kcal_per_100g": 950.0,
    "protein_per_100g": 100.0,
    "fat_per_100g": 100.0,
    "carbs_per_100g": 100.0,
    "fiber_per_100g": 100.0,
    "sugar_per_100g": 100.0,
    "saturated_fat_per_100g": 100.0,
    "salt_per_100g": 100.0,
    "liquid_ml_per_100g": 100.0,
}

REQUIRED_NUTRIENTS = (
    "kcal_per_100g",
    "protein_per_100g",
    "fat_per_100g",
    "carbs_per_100g",
    "liquid_ml_per_100g",
)
# Not everyone knows these for a homemade product: missing = unknown (NULL).
OPTIONAL_NUTRIENTS = (
    "fiber_per_100g",
    "sugar_per_100g",
    "saturated_fat_per_100g",
    "salt_per_100g",
)

MAX_PRODUCT_NAME_LENGTH = 120
MAX_GRAMS_PER_UNIT = 5000.0


def _number(raw, key):
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


def _nutrition_value(data, key):
    raw = data.get(key, 0)
    if raw in (None, ""):
        raw = 0
    return _number(raw, key)


def _optional_nutrition_value(data, key):
    """None (unknown) when missing or blank; an explicit 0 stays 0."""
    raw = data.get(key)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return None
    return _number(raw, key)


def _check_consistency(product):
    # Label values are rounded, so a part can never exceed its whole.
    if product.sugar_per_100g is not None and product.sugar_per_100g > product.carbs_per_100g:
        raise ProductServiceError("sugar_per_100g cannot exceed carbs_per_100g")
    if (
        product.saturated_fat_per_100g is not None
        and product.saturated_fat_per_100g > product.fat_per_100g
    ):
        raise ProductServiceError("saturated_fat_per_100g cannot exceed fat_per_100g")


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


def _product_name_value(data):
    name = " ".join(_text(data, "name").split())
    if not name:
        raise ProductServiceError("Product name is required")
    if len(name) > MAX_PRODUCT_NAME_LENGTH:
        raise ProductServiceError("Product name is too long")
    normalized = normalize_name(name)
    if not normalized:
        raise ProductServiceError("Product name must contain letters or digits")
    return name, normalized


def _ensure_unique_name(user_id, normalized, exclude_id=None):
    query = Product.query.filter(
        Product.owner_user_id == user_id,
        Product.is_active.is_(True),
        Product.normalized_name == normalized,
    )
    if exclude_id is not None:
        query = query.filter(Product.id != exclude_id)
    if db.session.query(query.exists()).scalar():
        raise ProductServiceError(
            "You already have a product with this name",
            "duplicate_product",
        )


def find_own_product_by_name(user_id, name):
    normalized = normalize_name(name)
    if not normalized:
        return None
    return Product.query.filter(
        Product.owner_user_id == user_id,
        Product.is_active.is_(True),
        Product.normalized_name == normalized,
    ).first()


def create_user_product(user_id, data, locale="uk"):
    locale = normalize_locale(locale)
    name, normalized = _product_name_value(data)

    unit = (_text(data, "default_unit") or "g").lower()
    if unit not in SUPPORTED_UNITS:
        raise ProductServiceError("Unsupported default unit")

    grams_per_unit = _grams_per_unit(data.get("grams_per_unit", 1))

    category = (_text(data, "category") or "other").lower()
    if category not in PRODUCT_CATEGORIES:
        raise ProductServiceError("Unsupported product category")

    _ensure_unique_name(user_id, normalized)

    product = Product(
        owner_user_id=user_id,
        source="user",
        normalized_name=normalized,
        brand=_text(data, "brand", MAX_BRAND_LENGTH) or None,
        # Barcodes are unique across all products; a user-chosen value could
        # collide with (and block) another user's product. Not used by the UI.
        barcode=None,
        category=category,
        default_unit=unit,
        grams_per_unit=grams_per_unit,
        data_source="user",
        verified=False,
    )
    for key in REQUIRED_NUTRIENTS:
        setattr(product, key, _nutrition_value(data, key))
    for key in OPTIONAL_NUTRIENTS:
        setattr(product, key, _optional_nutrition_value(data, key))
    _check_consistency(product)

    db.session.add(product)
    db.session.flush()

    db.session.add(
        ProductName(
            product_id=product.id,
            locale=locale,
            name=name,
            normalized_name=normalized,
        )
    )

    db.session.commit()
    return serialize_product(product, user_id, locale)


def update_user_product(user_id, product_id, data, locale="uk"):
    """Edit the user's own product.

    Logged entries keep the values they were logged with (each entry stores
    its own snapshot), so this never rewrites history.
    """
    product = get_user_product(user_id, product_id)
    if product is None or not product.is_active:
        return None

    locale = normalize_locale(locale)

    if "name" in data:
        name, normalized = _product_name_value(data)
        _ensure_unique_name(user_id, normalized, exclude_id=product.id)
        product.normalized_name = normalized

        # A user's product has one name; keep every locale row in sync so a
        # language switch never brings the old (wrong) name back.
        names = ProductName.query.filter_by(product_id=product.id).all()
        for localized in names:
            localized.name = name
            localized.normalized_name = normalized

        if not any(localized.locale == locale for localized in names):
            db.session.add(
                ProductName(
                    product_id=product.id,
                    locale=locale,
                    name=name,
                    normalized_name=normalized,
                )
            )

    for key in REQUIRED_NUTRIENTS:
        if key in data:
            setattr(product, key, _nutrition_value(data, key))
    for key in OPTIONAL_NUTRIENTS:
        if key in data:
            setattr(product, key, _optional_nutrition_value(data, key))
    _check_consistency(product)

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
        product.grams_per_unit = _grams_per_unit(data["grams_per_unit"])

    db.session.flush()
    db.session.expire(product, ["names"])
    db.session.commit()
    return serialize_product(product, user_id, locale)


def archive_user_product(user_id, product_id):
    product = get_user_product(user_id, product_id)
    if product is None:
        return False

    if not product.is_active:
        return False

    # Archived, not deleted: meals and dishes that already use it keep it.
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
