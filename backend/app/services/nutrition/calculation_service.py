from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace


SUPPORTED_UNITS = {"g", "ml", "pcs"}

# Upper bounds for a single entry. Anything above is almost certainly a typo
# (e.g. 50000 g instead of 500 g) and would wreck the day's totals.
MAX_AMOUNT_BY_UNIT = {"g": 5000.0, "ml": 5000.0, "pcs": 100.0}


class NutritionValidationError(ValueError):
    pass


@dataclass(frozen=True)
class CalculatedNutrition:
    grams: float
    calories: float
    protein: float
    fat: float
    carbs: float
    # None = unknown for this product; never replaced by 0.
    fiber: float | None
    liquid_ml: float
    sugar: float | None = None
    saturated_fat: float | None = None
    salt: float | None = None


# Per-100 g fields copied into every logged entry (MealItem.basis).
BASIS_FIELDS = (
    "kcal_per_100g",
    "protein_per_100g",
    "fat_per_100g",
    "carbs_per_100g",
    "fiber_per_100g",
    "sugar_per_100g",
    "saturated_fat_per_100g",
    "salt_per_100g",
    "liquid_ml_per_100g",
    "default_unit",
    "grams_per_unit",
)


def product_basis(product) -> dict:
    """Snapshot of the values an entry is calculated from."""
    return {field: getattr(product, field, None) for field in BASIS_FIELDS}


def basis_product(basis: dict):
    """A product-like object over a stored basis, for recalculation."""
    values = {field: basis.get(field) for field in BASIS_FIELDS}
    values["default_unit"] = values["default_unit"] or "g"
    values["grams_per_unit"] = values["grams_per_unit"] or 1
    for field in ("kcal_per_100g", "protein_per_100g", "fat_per_100g",
                  "carbs_per_100g", "liquid_ml_per_100g"):
        values[field] = values[field] or 0
    return SimpleNamespace(**values)


def _scale(per_100g, factor, digits=2):
    if per_100g is None:
        return None
    return round(max(per_100g, 0) * factor, digits)


def sum_known(values):
    """Sum of the known values, or None when none is known."""
    known = [value for value in values if value is not None]
    return round(sum(known), 2) if known else None


def partial_sum(values):
    """``(total, complete)`` for a nullable nutrient.

    ``total`` sums the known values; it is None when there are values but
    none is known (shown as "—", not "0 g"). Nothing at all is a known 0.
    ``complete`` is False when some values are unknown, so the total is a
    lower bound.
    """
    values = list(values)
    if not values:
        return 0.0, True
    return sum_known(values), all(value is not None for value in values)


def partial_totals(items, field):
    return partial_sum(getattr(item, field) for item in items)


def normalize_unit(unit: str | None, default: str = "g") -> str:
    normalized = (unit or default or "g").strip().lower()

    if normalized not in SUPPORTED_UNITS:
        raise NutritionValidationError(
            f"Unsupported unit: {normalized}"
        )

    return normalized


def normalize_amount(amount) -> float:
    try:
        value = float(amount)
    except (TypeError, ValueError):
        raise NutritionValidationError("Amount must be a number")

    if value != value or value <= 0:
        raise NutritionValidationError("Amount must be positive")

    return value


def validate_amount_for_unit(amount: float, unit: str) -> None:
    limit = MAX_AMOUNT_BY_UNIT.get(unit)

    if limit is not None and amount > limit:
        raise NutritionValidationError(
            f"Amount is too large (max {limit:g} {unit})"
        )


def amount_to_grams(amount, unit: str, grams_per_unit: float) -> float:
    amount_value = normalize_amount(amount)
    normalized_unit = normalize_unit(unit)

    try:
        conversion = float(grams_per_unit)
    except (TypeError, ValueError):
        raise NutritionValidationError("Invalid product unit conversion")

    if conversion <= 0:
        raise NutritionValidationError("Product unit conversion must be positive")

    if normalized_unit == "g":
        return amount_value

    return amount_value * conversion


def calculate_liquid_ml(
    amount: float,
    unit: str,
    grams: float,
    liquid_ml_per_100g: float,
) -> float:
    if liquid_ml_per_100g <= 0:
        return 0.0

    # Milliliters are already a volume. Do not route them through the
    # product's gram conversion when calculating hydration.
    if unit == "ml":
        return round(amount, 2)

    return round(
        liquid_ml_per_100g * grams / 100.0,
        2,
    )


def calculate_product_nutrition(product, amount, unit=None) -> CalculatedNutrition:
    normalized_unit = normalize_unit(unit, product.default_unit)
    amount_value = normalize_amount(amount)
    validate_amount_for_unit(amount_value, normalized_unit)
    grams = amount_to_grams(
        amount_value,
        normalized_unit,
        product.grams_per_unit,
    )

    factor = grams / 100.0

    liquid_ml_per_100g = max(
        getattr(product, "liquid_ml_per_100g", 0) or 0,
        0,
    )
    liquid_ml = calculate_liquid_ml(
        amount_value,
        normalized_unit,
        grams,
        liquid_ml_per_100g,
    )

    return CalculatedNutrition(
        grams=round(grams, 2),
        calories=round(max(product.kcal_per_100g, 0) * factor),
        protein=round(max(product.protein_per_100g, 0) * factor, 2),
        fat=round(max(product.fat_per_100g, 0) * factor, 2),
        carbs=round(max(product.carbs_per_100g, 0) * factor, 2),
        fiber=_scale(getattr(product, "fiber_per_100g", None), factor),
        liquid_ml=liquid_ml,
        sugar=_scale(getattr(product, "sugar_per_100g", None), factor),
        saturated_fat=_scale(getattr(product, "saturated_fat_per_100g", None), factor),
        salt=_scale(getattr(product, "salt_per_100g", None), factor, 3),
    )
