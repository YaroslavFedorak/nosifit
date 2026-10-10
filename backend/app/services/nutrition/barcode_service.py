"""Barcode lookup and import, shared by the website and the Telegram bot.

Lookup order for one user and one barcode:

1. the user's own active product with that barcode;
2. the shared catalog (``barcode``, or a seeded Open Food Facts label
   product whose ``source_ref`` is the barcode);
3. the cache of confirmed external answers (``nutrition_barcode_lookups``);
4. Open Food Facts, at most one request per barcode at a time (a
   PostgreSQL advisory lock) and within an app-wide outbound budget.

External data comes back as a *preview*: normalized to the Product model's
per-100 g convention and validated, with what is missing or invalid listed
separately. Nothing external is used by nutrition calculations until the
user imports it, and the import re-reads the cached answer on the server:
clients send only the barcode, never nutrition values.

Imported products go to the user's own products (``source = "user"``,
``data_source = "open_food_facts"``, ``source_ref`` = barcode, never
``verified``): private, and editable or deletable when the community data
is wrong. Each user gets one per barcode (the per-user barcode index makes
a concurrent second import fall back to the first); other users reuse the
cached answer. Existing products are never overwritten, and meal entries
keep their own snapshots anyway.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from flask import current_app
from sqlalchemy import and_, or_, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import selectinload

from backend.app.extensions import db
from backend.app.models import BarcodeLookup, Product, ProductName
from backend.app.services.nutrition import open_food_facts
from backend.app.services.nutrition.barcode import (
    InvalidBarcode,
    barcode_variants,
    normalize_barcode,
)
from backend.app.services.nutrition.open_food_facts import (
    OpenFoodFactsUnavailable,
)
from backend.app.services.nutrition.product_service import (
    MAX_BRAND_LENGTH,
    MAX_PRODUCT_NAME_LENGTH,
    NUTRITION_LIMITS,
    SUPPORTED_LOCALES,
    normalize_locale,
    serialize_product,
)
from backend.app.utils.name_normalization import normalize_name

logger = logging.getLogger(__name__)

ATTRIBUTION = (
    "Open Food Facts contributors, https://world.openfoodfacts.org "
    "(Open Database License 1.0)"
)

REQUIRED_FIELDS = (
    "kcal_per_100g",
    "protein_per_100g",
    "fat_per_100g",
    "carbs_per_100g",
)
OPTIONAL_FIELDS = (
    "fiber_per_100g",
    "sugar_per_100g",
    "saturated_fat_per_100g",
    "salt_per_100g",
)
# Product field -> Open Food Facts nutriment name.
OFF_NUTRIENTS = {
    "kcal_per_100g": "energy-kcal",
    "protein_per_100g": "proteins",
    "fat_per_100g": "fat",
    "carbs_per_100g": "carbohydrates",
    "fiber_per_100g": "fiber",
    "sugar_per_100g": "sugars",
    "saturated_fat_per_100g": "saturated-fat",
    "salt_per_100g": "salt",
}
KJ_PER_KCAL = 4.184
SALT_PER_SODIUM = 2.5
# Labels round each value, so a part may exceed its whole by a little.
ROUNDING_TOLERANCE_G = 0.5
# Protein + fat + carbs + fiber cannot weigh more than the 100 g they are in.
MAX_MACRO_MASS_G = 105.0
# Larger serving sizes are not plausible label servings.
MAX_SERVING_QUANTITY = 2000.0
LOCK_TIMEOUT = "10s"
# Expired "found" answers are kept this long as a fallback for outages.
STALE_GRACE = timedelta(days=30)

_LIQUID_UNITS = {"ml", "cl", "dl", "l", "мл", "л", "fl oz"}
_LIQUID_QUANTITY = re.compile(r"\d\s*(ml|cl|dl|l|мл|л)\b", re.IGNORECASE)
_SOLID_QUANTITY = re.compile(r"\d\s*(g|kg|mg|г|кг)\b", re.IGNORECASE)
_SERVING_GRAMS = re.compile(r"(\d+(?:[.,]\d+)?)\s*(g|г|ml|мл)\b", re.IGNORECASE)


class BarcodeLookupError(Exception):
    def __init__(self, message: str, code: str, status: int = 400):
        super().__init__(message)
        self.code = code
        self.status = status


@dataclass
class ExternalAnswer:
    status: str  # "found" | "not_found"
    payload: dict | None
    fetched_at: datetime
    stale: bool = False


# --- normalization and validation --------------------------------------------


def _number(value):
    """``(number, None)``, or ``(None, "invalid")`` for non-numeric data."""
    if isinstance(value, bool):
        return None, "invalid"
    if isinstance(value, (int, float)):
        number = float(value)
        if number != number or number in (float("inf"), float("-inf")):
            return None, "invalid"
        return number, None
    return None, "invalid"


_SOLID_UNITS = {"g", "kg", "mg"}


def _unit(value) -> str:
    return str(value or "").strip().lower()


def _is_liquid(product: dict) -> bool | None:
    """True / False when the package says per 100 ml / 100 g, None if unclear.

    Open Food Facts gives ``*_100g`` per 100 ml for liquids. Only the package
    (``product_quantity_unit``, else ``quantity``) decides: a serving in ml
    on a product sold by weight (yoghurt "500 g", serving "250 ml") is not a
    drink. Without package evidence the basis stays uncertain.
    """
    package = _unit(product.get("product_quantity_unit"))
    if package in _LIQUID_UNITS:
        return True
    if package in _SOLID_UNITS:
        return False
    quantity = product.get("quantity") or ""
    liquid = bool(_LIQUID_QUANTITY.search(quantity))
    solid = bool(_SOLID_QUANTITY.search(quantity))
    if liquid != solid:
        return liquid
    serving = _unit(product.get("serving_quantity_unit"))
    if not serving:
        match = _SERVING_GRAMS.search(product.get("serving_size") or "")
        serving = _unit(match.group(2)) if match else ""
    if not liquid and serving in _SOLID_UNITS | {"г"}:
        return False
    return None


def _serving_quantity(product: dict, liquid: bool | None) -> float | None:
    """Serving size in the basis unit (g, or ml for liquids) when stated.

    A serving in another unit than the basis (ml for a product per 100 g)
    is not converted: that would need the unknown density.
    """
    value, _ = _number(product.get("serving_quantity"))
    unit = _unit(product.get("serving_quantity_unit"))
    match = _SERVING_GRAMS.search(product.get("serving_size") or "")
    if value is None and match:
        value = float(match.group(1).replace(",", "."))
    if not unit:
        unit = _unit(match.group(2)) if match else "g"
    unit = {"г": "g", "мл": "ml"}.get(unit, unit)
    if liquid is None or unit != ("ml" if liquid else "g"):
        return None
    if value is None or value <= 0 or value > MAX_SERVING_QUANTITY:
        return None
    return value


def _pick_names(product: dict, locale: str) -> dict[str, str]:
    """Names per supported locale, plus the main name under its language."""
    names = {}
    for code in SUPPORTED_LOCALES:
        name = _clean_name(product.get(f"product_name_{code}"))
        if name:
            names[code] = name
    main = _clean_name(product.get("product_name"))
    if main:
        lang = str(product.get("lang") or "").lower()
        key = lang if lang in SUPPORTED_LOCALES else "en"
        names.setdefault(key, main)
    return names


def _clean_name(value) -> str | None:
    if not isinstance(value, str):
        return None
    printable = "".join(ch if ch.isprintable() else " " for ch in value)
    name = " ".join(printable.split())[:MAX_PRODUCT_NAME_LENGTH].strip()
    return name if normalize_name(name) else None


def _brand(product: dict) -> str | None:
    brands = product.get("brands")
    if not isinstance(brands, str):
        return None
    first = "".join(ch if ch.isprintable() else " " for ch in brands.split(",")[0])
    first = " ".join(first.split())
    return first[:MAX_BRAND_LENGTH] or None


def normalize_external_product(product: dict, locale: str = "uk") -> dict:
    """Preview of an external product in NosiFit's per-100 g convention.

    Never invents data: a missing value stays missing (``None``, listed in
    ``missing``), an unusable one is listed in ``invalid`` with a reason,
    and nothing is clamped. ``importable`` is True only when the name and
    every required value are present and every present value is valid.
    """
    locale = normalize_locale(locale)
    nutriments = product.get("nutriments") if isinstance(product.get("nutriments"), dict) else {}
    liquid = _is_liquid(product)
    serving = _serving_quantity(product, liquid)

    values: dict[str, float | None] = {}
    invalid: dict[str, str] = {}
    warnings: list[str] = []
    converted = set()

    def per_100(name):
        """Value per 100 g/ml from ``_100g``, else from ``_serving``."""
        key_100 = f"{name}_100g"
        if key_100 in nutriments:
            return _number(nutriments[key_100]) + (False,)
        key_serving = f"{name}_serving"
        if key_serving in nutriments and serving is not None:
            value, error = _number(nutriments[key_serving])
            if value is None:
                return None, error, True
            return value * 100.0 / serving, None, True
        return None, None, False

    for field, name in OFF_NUTRIENTS.items():
        value, error, from_serving = per_100(name)
        if field == "kcal_per_100g" and value is None and error is None:
            # Energy given only in kJ ("energy" is kJ in Open Food Facts).
            for kj_name in ("energy-kj", "energy"):
                kj, error, from_serving = per_100(kj_name)
                if kj is not None or error:
                    value = None if kj is None else kj / KJ_PER_KCAL
                    if kj is not None:
                        warnings.append("energy_from_kj")
                    break
        if field == "salt_per_100g" and value is None and error is None:
            sodium, error, from_serving = per_100("sodium")
            if sodium is not None:
                value = sodium * SALT_PER_SODIUM
                warnings.append("salt_from_sodium")
        if error:
            invalid[field] = "not_a_number"
            values[field] = None
            continue
        if value is not None and from_serving:
            converted.add(field)
        values[field] = value

    # Range checks: reported, never clamped.
    for field, value in values.items():
        if value is None:
            continue
        if value < 0:
            invalid[field] = "negative"
        elif value > NUTRITION_LIMITS[field]:
            invalid[field] = "too_large"

    def known(field):
        return values.get(field) if field not in invalid else None

    carbs, fat = known("carbs_per_100g"), known("fat_per_100g")
    sugar, saturated = known("sugar_per_100g"), known("saturated_fat_per_100g")
    if sugar is not None and carbs is not None and sugar > carbs + ROUNDING_TOLERANCE_G:
        invalid["sugar_per_100g"] = "exceeds_carbs"
    if saturated is not None and fat is not None and saturated > fat + ROUNDING_TOLERANCE_G:
        invalid["saturated_fat_per_100g"] = "exceeds_fat"

    mass = [known(f) for f in ("protein_per_100g", "fat_per_100g", "carbs_per_100g")]
    if all(v is not None for v in mass):
        total_mass = sum(mass) + (known("fiber_per_100g") or 0)
        if total_mass > MAX_MACRO_MASS_G:
            for field in ("protein_per_100g", "fat_per_100g", "carbs_per_100g"):
                invalid.setdefault(field, "macros_exceed_100g")

        kcal = known("kcal_per_100g")
        if kcal is not None and not any(f in invalid for f in REQUIRED_FIELDS):
            protein, fat_value, carbs_value = mass
            expected = 4 * protein + 9 * fat_value + 4 * carbs_value + 2 * (known("fiber_per_100g") or 0)
            # Far less energy than the macros contain cannot be explained
            # (polyols and alcohol only push the other way or a little).
            if kcal < 0.5 * expected - 20:
                invalid["kcal_per_100g"] = "inconsistent_with_macros"
            elif abs(kcal - expected) > max(50.0, 0.25 * expected):
                warnings.append("energy_mismatch")

    if converted:
        warnings.append("converted_from_serving")
    if liquid:
        # Values are per 100 ml. Logged in ml they are exact; the density is
        # unknown, so 1 g/ml is used for grams (the catalog's ml convention).
        warnings.append("per_100ml")
    elif liquid is None:
        # Not known whether the values are per 100 g or per 100 ml: shown as
        # per 100 g and flagged, never converted with a guessed density.
        warnings.append("basis_uncertain")

    names = _pick_names(product, locale)
    name = names.get(locale) or names.get("en") or names.get("uk") or next(iter(names.values()), None)

    missing = []
    if not name:
        missing.append("name")
    missing.extend(f for f in REQUIRED_FIELDS if values.get(f) is None and f not in invalid)
    missing_optional = [f for f in OPTIONAL_FIELDS if values.get(f) is None and f not in invalid]
    if str(product.get("no_nutrition_data") or "").lower() in ("on", "true", "1"):
        warnings.append("no_nutrition_data")

    rounded = {}
    for field, value in values.items():
        if value is None or field in invalid:
            rounded[field] = None
        else:
            rounded[field] = round(value, 3 if field == "salt_per_100g" else 2)

    complete = not missing
    return {
        "name": name,
        "names": names,
        "brand": _brand(product),
        **rounded,
        "default_unit": "ml" if liquid else "g",
        "grams_per_unit": 1.0,
        "basis": "100ml" if liquid else "100g",
        "missing": missing,
        "missing_optional": missing_optional,
        "invalid": invalid,
        "warnings": sorted(set(warnings)),
        "complete": complete,
        "importable": complete and not invalid,
    }


# --- local catalog -------------------------------------------------------------


def find_local_product(user_id, code: str):
    """The user's own product, else the catalog product with ``code``."""
    variants = barcode_variants(code)
    base = Product.query.options(selectinload(Product.names)).filter(Product.is_active.is_(True))

    own = base.filter(
        Product.owner_user_id == user_id,
        Product.barcode.in_(variants),
    ).order_by(Product.id).first()
    if own is not None:
        return own

    return (
        base.filter(
            Product.owner_user_id.is_(None),
            or_(
                Product.barcode.in_(variants),
                and_(
                    Product.data_source == open_food_facts.PROVIDER,
                    Product.source_ref.in_(variants),
                ),
            ),
        )
        # A row that carries the barcode itself wins over a source_ref match.
        .order_by(Product.barcode.is_(None), Product.id)
        .first()
    )


def _catalog_barcode_taken(code: str) -> bool:
    """An archived catalog product still owns its barcode."""
    return db.session.query(
        Product.query.filter(
            Product.owner_user_id.is_(None),
            Product.barcode == code,
        ).exists()
    ).scalar()


# --- external lookup with cache ---------------------------------------------------


def _now() -> datetime:
    return datetime.utcnow()


def _ttl(status: str) -> timedelta:
    config = current_app.config
    if status == "found":
        return timedelta(days=int(config.get("OFF_CACHE_FOUND_DAYS", 30)))
    return timedelta(days=int(config.get("OFF_CACHE_NOT_FOUND_DAYS", 7)))


def _outbound_allowed() -> bool:
    from web.app.security import hit_limit

    per_minute = int(current_app.config.get("OFF_MAX_REQUESTS_PER_MINUTE", 10))
    return not hit_limit("off_outbound", "global", per_minute, 60)


def _answer(row: BarcodeLookup, stale=False) -> ExternalAnswer:
    return ExternalAnswer(row.status, row.payload, row.fetched_at, stale)


def external_lookup(code: str) -> ExternalAnswer:
    """Confirmed external answer for ``code``, from the cache when fresh.

    Raises ``OpenFoodFactsUnavailable`` when there is no fresh or stale
    answer and Open Food Facts cannot be asked right now.
    """
    row = db.session.get(BarcodeLookup, code)
    if row is not None and row.expires_at > _now():
        return _answer(row)

    # One request per barcode at a time across all workers: the others wait
    # here and then read the answer the first one stored.
    try:
        db.session.execute(text(f"SET LOCAL lock_timeout = '{LOCK_TIMEOUT}'"))
        db.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
            {"key": f"nosifit:barcode:{code}"},
        )
    except OperationalError:
        db.session.rollback()
        raise OpenFoodFactsUnavailable("busy")

    row = db.session.get(BarcodeLookup, code, populate_existing=True)
    if row is not None and row.expires_at > _now():
        db.session.rollback()  # releases the lock
        return _answer(row)

    try:
        if not _outbound_allowed():
            raise OpenFoodFactsUnavailable("rate_limited")
        answer = open_food_facts.fetch_product(code)
    except OpenFoodFactsUnavailable:
        if row is not None and row.status == "found":
            stale = _answer(row, stale=True)
            db.session.rollback()
            return stale
        db.session.rollback()
        raise

    now = _now()
    if row is None:
        row = BarcodeLookup(barcode=code)
        db.session.add(row)
    row.provider = open_food_facts.PROVIDER
    row.status = answer.status
    row.payload = answer.product
    row.fetched_at = now
    row.expires_at = now + _ttl(answer.status)
    # Bounded table: expired rows past the stale grace are dropped.
    BarcodeLookup.query.filter(
        BarcodeLookup.expires_at < now - STALE_GRACE
    ).delete(synchronize_session=False)
    db.session.commit()
    return ExternalAnswer(answer.status, answer.product, now)


# --- public API ------------------------------------------------------------------


def _parse(raw) -> str:
    try:
        return normalize_barcode(raw)
    except InvalidBarcode as exc:
        raise BarcodeLookupError(str(exc), "invalid_barcode", 400)


def _unavailable(exc: OpenFoodFactsUnavailable) -> BarcodeLookupError:
    return BarcodeLookupError(
        "Product lookup is temporarily unavailable",
        "lookup_unavailable",
        503,
    )


def lookup_barcode(user_id, raw, locale="uk") -> dict:
    """What NosiFit knows about a scanned barcode (nothing is stored here
    except the cache of the external answer)."""
    locale = normalize_locale(locale)
    code = _parse(raw)

    product = find_local_product(user_id, code)
    if product is not None:
        return {
            "barcode": code,
            "status": "found",
            "source": "catalog",
            "product": serialize_product(product, user_id, locale),
        }

    if _catalog_barcode_taken(code):
        # Archived on purpose: do not bring it back from outside.
        return {"barcode": code, "status": "not_found", "source": "catalog"}

    try:
        answer = external_lookup(code)
    except OpenFoodFactsUnavailable as exc:
        raise _unavailable(exc)

    if answer.status != "found" or not answer.payload:
        return {"barcode": code, "status": "not_found", "source": open_food_facts.PROVIDER}

    preview = normalize_external_product(answer.payload, locale)
    preview.update({
        "barcode": code,
        "data_source": open_food_facts.PROVIDER,
        "source_ref": code,
        "verified": False,
    })
    return {
        "barcode": code,
        "status": "found",
        "source": open_food_facts.PROVIDER,
        "preview": preview,
        "stale": answer.stale,
        "fetched_at": answer.fetched_at.isoformat(timespec="seconds") + "Z",
        "attribution": ATTRIBUTION,
    }


def _own_product_name(user_id, name: str, brand: str | None) -> tuple[str, str]:
    """``(name, normalized)`` free among the user's active products.

    A user may already have a product with the same name (typed by hand):
    the brand is added to tell them apart; if that is taken too, it is a
    duplicate the user has to resolve.
    """
    candidates = [name]
    if brand:
        candidates.append(f"{name[:MAX_PRODUCT_NAME_LENGTH - len(brand) - 3]} ({brand})")
    for candidate in candidates:
        normalized = normalize_name(candidate)[:160]
        taken = Product.query.filter(
            Product.owner_user_id == user_id,
            Product.is_active.is_(True),
            Product.normalized_name == normalized,
        ).exists()
        if not db.session.query(taken).scalar():
            return candidate, normalized
    raise BarcodeLookupError(
        "You already have a product with this name", "duplicate_product", 409
    )


def import_barcode_product(user_id, raw, locale="uk") -> tuple[dict, bool]:
    """Adds the scanned product to the user's own products ("My products").

    The copy is private and editable like any own product, so wrong
    community data can be corrected or deleted by the user without touching
    anyone else; logged entries keep their own snapshots either way. It keeps
    its origin (``data_source`` / ``source_ref``) and is never ``verified``.

    Returns ``(serialized product, created)``. A product the user already
    sees for this barcode (their own, or a catalog one) is returned
    unchanged; values always come from the server-side answer, so a client
    cannot inject nutrition data.
    """
    locale = normalize_locale(locale)
    code = _parse(raw)

    existing = find_local_product(user_id, code)
    if existing is not None:
        return serialize_product(existing, user_id, locale), False

    if _catalog_barcode_taken(code):
        raise BarcodeLookupError("Product not found", "product_not_found", 404)

    try:
        answer = external_lookup(code)
    except OpenFoodFactsUnavailable as exc:
        raise _unavailable(exc)

    if answer.status != "found" or not answer.payload:
        raise BarcodeLookupError("Product not found", "product_not_found", 404)

    preview = normalize_external_product(answer.payload, locale)
    if preview["invalid"]:
        raise BarcodeLookupError(
            "The product data is not plausible", "invalid_product_data", 422
        )
    if not preview["importable"]:
        raise BarcodeLookupError(
            "The product data is incomplete", "incomplete_product", 422
        )

    name, normalized = _own_product_name(user_id, preview["name"], preview["brand"])
    product = Product(
        owner_user_id=user_id,
        source="user",
        barcode=code,
        normalized_name=normalized,
        brand=preview["brand"],
        category="other",
        default_unit=preview["default_unit"],
        grams_per_unit=preview["grams_per_unit"],
        # Whether a drink counts towards hydration is not in the data.
        liquid_ml_per_100g=0,
        data_source=open_food_facts.PROVIDER,
        source_ref=code,
        verified=False,
    )
    for field in REQUIRED_FIELDS + OPTIONAL_FIELDS:
        setattr(product, field, preview[field])

    try:
        with db.session.begin_nested():
            db.session.add(product)
            db.session.flush()
            # One name, like every own product (edits keep locales in sync).
            db.session.add(ProductName(product_id=product.id, locale=locale, name=name))
            db.session.flush()
    except IntegrityError:
        # The same user imported it a moment earlier (a double tap).
        db.session.rollback()
        winner = find_local_product(user_id, code)
        if winner is None:
            raise BarcodeLookupError(
                "You already have a product with this name", "duplicate_product", 409
            )
        return serialize_product(winner, user_id, locale), False

    # The cached answer stays: other users scanning the code reuse it.
    db.session.commit()
    db.session.expire(product, ["names"])
    logger.info("Imported barcode product %s from Open Food Facts", product.id)
    return serialize_product(product, user_id, locale), True
