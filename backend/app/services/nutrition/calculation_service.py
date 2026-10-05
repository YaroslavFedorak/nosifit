from __future__ import annotations

from dataclasses import dataclass


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
    fiber: float
    liquid_ml: float


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
        fiber=round(max(product.fiber_per_100g, 0) * factor, 2),
        liquid_ml=liquid_ml,
    )
