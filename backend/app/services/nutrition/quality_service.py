"""Diet quality of a day: classification of foods and a 0-100 score.

The full description (scale, weights, references, limitations) is in
``docs/nutrition-model.md``. In short:

* Every food is classified from its canonical category (``Product.category``,
  never a localized name) and, where the category alone cannot tell, from its
  nutrients: ``whole`` (minimally processed), ``processed``, ``neutral``
  (staples, culinary ingredients, mixed dishes, drinks) or ``unknown``. A food
  is in exactly one class.
* The score combines six components, each measured against the energy that
  was actually eaten (shares of energy, or grams per 1000 kcal), so 300 kcal
  and 3000 kcal of the same food score the same: quality is about
  composition, not amount. A component whose nutrient is unknown for most of
  the energy is left out, never scored as zero.
* ``None`` means "cannot say" (nothing logged, or too little energy logged to
  judge); it is never replaced by 0.

All thresholds are named constants below, each marked with where it comes
from (a published reference, or a product policy).
"""
from __future__ import annotations

WHOLE = "whole"
PROCESSED = "processed"
NEUTRAL = "neutral"
UNKNOWN = "unknown"

# --- classification -------------------------------------------------------

# Minimally processed by nature (NOVA group 1-like). Whether a given product
# is still that - sausage is a "meat", sweetened yoghurt is "dairy" - is
# decided by the guards below, not by the category.
WHOLE_CATEGORIES = frozenset({
    "fruits", "vegetables", "berries", "legumes", "nuts", "seeds",
    "fish", "seafood", "poultry", "meat", "eggs", "dairy",
})
# Cereal foods: whole grain or refined, told apart by fibre density.
CEREAL_CATEGORIES = frozenset({"grains", "pasta", "bread"})
# Confectionery, snacks and fast food are processed by definition.
PROCESSED_CATEGORIES = frozenset({"sweets", "snacks", "fast_food"})
# Culinary ingredients, traditional processed foods, drinks and dishes whose
# recipe is unknown: neither "whole" nor "processed" can be claimed.
NEUTRAL_CATEGORIES = frozenset({
    "oils", "cheese", "sauces", "ingredients", "prepared", "beverages",
})

# Guards are per 100 g. Salt 1.5 g and total sugars 22.5 g are the "high"
# bands of the UK front-of-pack nutrient criteria (Department of Health,
# 2016); 5 g sugars is the "low" band, which sits just above the lactose of
# plain milk and yoghurt (<= 5 g in the catalog) and below sweetened ones
# (>= 11 g).
HIGH_SALT_G_PER_100G = 1.5
HIGH_SUGAR_G_PER_100G = 22.5
PLAIN_DAIRY_SUGAR_G_PER_100G = 5.0

# Categories where a high salt content marks curing, brining or canning
# (ham, sausage, smoked or salted fish, canned or pickled vegetables, salted
# nuts). The salt value is then needed to call the food "whole".
SALT_GUARDED = frozenset({
    "meat", "poultry", "fish", "seafood", "legumes", "vegetables", "nuts",
    "seeds",
})
# Categories where sugar marks a sweetened product, with the limit per 100 g.
SUGAR_GUARDED = {
    "dairy": PLAIN_DAIRY_SUGAR_G_PER_100G,
    "grains": HIGH_SUGAR_G_PER_100G,
    "pasta": HIGH_SUGAR_G_PER_100G,
    "bread": HIGH_SUGAR_G_PER_100G,
    "legumes": HIGH_SUGAR_G_PER_100G,
    "nuts": HIGH_SUGAR_G_PER_100G,
    "seeds": HIGH_SUGAR_G_PER_100G,
    "sauces": HIGH_SUGAR_G_PER_100G,
}
# Without the sugar value the guard cannot be evaluated: only these
# categories are then "unknown" instead of assumed unsweetened.
SUGAR_REQUIRED = frozenset({"dairy"})
SALT_GUARDED_NEUTRAL = frozenset({"sauces"})

# Butter and other milk fats are culinary ingredients, not "dairy" foods in
# the sense above. EU Regulation 1308/2013 defines butter as at least 80%
# milk fat, which is the marker used.
DAIRY_FAT_G_PER_100G = 80.0

# Fibre per 100 kcal that makes a cereal food whole grain: the EU
# "source of fibre" claim (Regulation 1924/2006: 3 g/100 g or 1.5 g/100 kcal).
# Per energy, so cooked and dry foods are judged alike.
WHOLE_GRAIN_FIBRE_G_PER_100KCAL = 1.5

# --- score ----------------------------------------------------------------

# Product policy: at least this share of energy from whole foods earns the
# full "whole foods" mark; this share of processed energy earns none.
WHOLE_SHARE_TARGET = 0.50
PROCESSED_SHARE_LIMIT = 0.50

# Fibre: grams per 1000 kcal when the user has no fibre/calorie target.
# 14 g per 1000 kcal is the US Dietary Reference Intake used by the NosiFit
# default (30 g at roughly 2100 kcal).
DEFAULT_FIBRE_G_PER_1000KCAL = 14.0

# WHO guidelines: free sugars and saturated fat < 10% of energy, salt < 5 g/day
# (taken as 2.5 g per 1000 kcal, the 5 g at the 2000 kcal reference diet).
# Total sugars are not free sugars: see ``added_sugar_grams``.
SUGAR_ENERGY_LIMIT = 0.10
SATURATED_FAT_ENERGY_LIMIT = 0.10
SALT_G_PER_1000KCAL_LIMIT = 2.5
REFERENCE_DAILY_KCAL = 2000.0

SUGAR_KCAL_PER_G = 4.0
FAT_KCAL_PER_G = 9.0

# Weights of the components (product policy, sum 100).
WEIGHTS = {
    "whole_foods": 30,
    "processed_foods": 15,
    "fiber": 20,
    "sugar": 15,
    "saturated_fat": 10,
    "salt": 10,
}

# A share or density is only trusted when this part of the energy is
# informed (classified, or has the nutrient known). Product policy: the
# majority of the energy.
MIN_COVERAGE = 0.5
# The day is only scored once this share of the calorie target (or of the
# 2000 kcal reference without a target) is logged, so a snack cannot stand
# for the whole day. Product policy.
MIN_SCORED_ENERGY_FRACTION = 0.25

# Groups whose sugars are intrinsic: never counted as added.
NATURAL_SUGAR_CATEGORIES = frozenset({
    "fruits", "berries", "vegetables", "legumes", "nuts", "seeds",
})


def _num(value):
    """A float, or None for anything that is not a usable number."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def classify_food(category, kcal=None, fiber=None, sugar=None, salt=None,
                  fat=None) -> str:
    """The class of one food from its category and nutrients.

    The nutrients are per 100 g (``kcal`` and ``fiber`` only as a ratio, but
    the salt, sugar and fat limits are per 100 g). ``None`` means unknown,
    never zero.
    """
    category = (category or "").strip().lower() or None
    kcal, fiber, sugar, salt, fat = (_num(v) for v in (kcal, fiber, sugar, salt, fat))

    if category in PROCESSED_CATEGORIES:
        return PROCESSED

    if category in CEREAL_CATEGORIES:
        if sugar is not None and sugar > SUGAR_GUARDED[category]:
            return PROCESSED
        if salt is not None and salt > HIGH_SALT_G_PER_100G:
            return PROCESSED
        if fiber is None or kcal is None:
            return UNKNOWN
        if kcal > 0 and fiber / kcal * 100 >= WHOLE_GRAIN_FIBRE_G_PER_100KCAL:
            return WHOLE
        return NEUTRAL

    if category in WHOLE_CATEGORIES:
        if category == "dairy" and fat is not None and fat >= DAIRY_FAT_G_PER_100G:
            return NEUTRAL
        if category in SALT_GUARDED:
            if salt is None:
                return UNKNOWN
            if salt > HIGH_SALT_G_PER_100G:
                return PROCESSED
        if category in SUGAR_GUARDED:
            if sugar is None and category in SUGAR_REQUIRED:
                return UNKNOWN
            if sugar is not None and sugar > SUGAR_GUARDED[category]:
                return PROCESSED
        return WHOLE

    if category in NEUTRAL_CATEGORIES:
        if category in SALT_GUARDED_NEUTRAL and salt is not None \
                and salt > HIGH_SALT_G_PER_100G:
            return PROCESSED
        if category in SUGAR_GUARDED and sugar is not None \
                and sugar > SUGAR_GUARDED[category]:
            return PROCESSED
        return NEUTRAL

    return UNKNOWN


def classify_item(item: dict) -> str:
    """The class of a logged entry (see :func:`quality_item_from_entry`).

    The guards need values per 100 g, so they are derived from the entry's
    own amounts: an entry whose grams are unknown or zero cannot be judged by
    its nutrients and falls back to the category alone.
    """
    category = item.get("category")
    grams = _num(item.get("grams"))
    kcal = _num(item.get("calories"))

    def per_100g(value):
        value = _num(value)
        if value is None or grams is None or grams <= 0:
            return None
        return value / grams * 100

    if grams is None or grams <= 0:
        # No amount to scale by: only the category is usable.
        if category in PROCESSED_CATEGORIES:
            return PROCESSED
        if category in NEUTRAL_CATEGORIES:
            return NEUTRAL
        if category in WHOLE_CATEGORIES and category not in SALT_GUARDED \
                and category not in SUGAR_REQUIRED:
            return WHOLE
        return UNKNOWN

    return classify_food(
        category,
        kcal=per_100g(kcal),
        fiber=per_100g(item.get("fiber")),
        sugar=per_100g(item.get("sugar")),
        salt=per_100g(item.get("salt")),
        fat=per_100g(item.get("fat")),
    )


def added_sugar_grams(item: dict):
    """Sugar of an entry that is not intrinsic to the food (a proxy).

    Free sugars are not in the data, only total sugars. Sugars of fruit,
    berries, vegetables, legumes, nuts and seeds are intrinsic; in dairy the
    lactose (up to 5 g per 100 g) is. Everything else counts in full.
    ``None`` when the sugar is unknown.
    """
    sugar = _num(item.get("sugar"))
    if sugar is None:
        return None
    category = item.get("category")
    if category in NATURAL_SUGAR_CATEGORIES:
        return 0.0
    if category == "dairy":
        grams = _num(item.get("grams"))
        if grams is None or grams <= 0:
            return None
        return max(sugar - PLAIN_DAIRY_SUGAR_G_PER_100G * grams / 100.0, 0.0)
    return sugar


def _clamp01(value):
    return max(0.0, min(1.0, value))


def _limit_score(value, limit):
    """100 at or under the limit, falling to 0 at twice the limit."""
    if limit <= 0:
        return None
    if value <= limit:
        return 100.0
    return 100.0 * _clamp01(2.0 - value / limit)


def energy_floor_kcal(goals):
    """The logged energy below which a day is not scored."""
    goal = _num((goals or {}).get("calories"))
    reference = goal if goal and goal > 0 else REFERENCE_DAILY_KCAL
    return reference * MIN_SCORED_ENERGY_FRACTION


def fiber_target_density(goals):
    """Grams of fibre per 1000 kcal the user is aiming for."""
    goals = goals or {}
    fiber_goal = _num(goals.get("fiber"))
    calories = _num(goals.get("calories"))
    if fiber_goal and fiber_goal > 0 and calories and calories > 0:
        return fiber_goal / calories * 1000.0
    return DEFAULT_FIBRE_G_PER_1000KCAL


def _empty_result(reason):
    return {
        "score": None,
        "reason": reason,
        "whole_foods_percent": 0,
        "processed_foods_percent": 0,
        "neutral_percent": 0,
        "unclassified_percent": 0,
        "fiber": None,
        "fiber_complete": True,
        "energy_kcal": 0,
        "components": {},
    }


def calculate_quality(ration_items, goals=None):
    """Quality of a set of logged entries (normally one day).

    ``ration_items`` are dicts (see :func:`quality_item_from_entry`) with
    ``category``, ``grams``, ``calories`` and the nullable ``fiber``,
    ``sugar``, ``saturated_fat`` and ``salt`` of the entry. ``goals`` are the
    day's targets (``calories``, ``fiber``); without them defaults apply.

    Percentages are shares of all logged energy and, with the neutral and
    unclassified shares, add up to 100 (up to rounding).
    """
    items = [item for item in (ration_items or []) if item]
    total_kcal = 0.0
    by_class = {WHOLE: 0.0, PROCESSED: 0.0, NEUTRAL: 0.0, UNKNOWN: 0.0}
    nutrient_kcal = {key: 0.0 for key in ("fiber", "sugar", "saturated_fat", "salt")}
    nutrient_sum = {key: 0.0 for key in nutrient_kcal}
    fiber_all_known = True

    for item in items:
        kcal = _num(item.get("calories"))
        kcal = kcal if kcal and kcal > 0 else 0.0
        total_kcal += kcal
        by_class[classify_item(item)] += kcal

        values = {
            "fiber": _num(item.get("fiber")),
            "sugar": added_sugar_grams(item),
            "saturated_fat": _num(item.get("saturated_fat")),
            "salt": _num(item.get("salt")),
        }
        if values["fiber"] is None:
            fiber_all_known = False
        for key, value in values.items():
            if value is None:
                continue
            nutrient_sum[key] += max(value, 0.0)
            nutrient_kcal[key] += kcal

    if not items:
        return _empty_result("no_data")

    fiber_known = any(_num(item.get("fiber")) is not None for item in items)
    fiber_total = round(nutrient_sum["fiber"], 1) if fiber_known else None

    if total_kcal <= 0:
        result = _empty_result("no_energy")
        result["fiber"] = fiber_total
        result["fiber_complete"] = fiber_all_known
        return result

    def percent(value):
        return round(value / total_kcal * 100)

    result = {
        "score": None,
        "reason": None,
        "whole_foods_percent": percent(by_class[WHOLE]),
        "processed_foods_percent": percent(by_class[PROCESSED]),
        "neutral_percent": percent(by_class[NEUTRAL]),
        "unclassified_percent": percent(by_class[UNKNOWN]),
        "fiber": fiber_total,
        "fiber_complete": fiber_all_known,
        "energy_kcal": round(total_kcal),
        "components": {},
    }

    if total_kcal < energy_floor_kcal(goals):
        result["reason"] = "low_energy"
        return result

    components = {}
    classified = total_kcal - by_class[UNKNOWN]
    if classified / total_kcal >= MIN_COVERAGE:
        components["whole_foods"] = {
            "value": by_class[WHOLE] / classified,
            "score": 100.0 * _clamp01(by_class[WHOLE] / classified / WHOLE_SHARE_TARGET),
        }
        components["processed_foods"] = {
            "value": by_class[PROCESSED] / classified,
            "score": 100.0 * _clamp01(1.0 - by_class[PROCESSED] / classified / PROCESSED_SHARE_LIMIT),
        }

    def density(key):
        if nutrient_kcal[key] <= 0 or nutrient_kcal[key] / total_kcal < MIN_COVERAGE:
            return None
        return nutrient_sum[key] / nutrient_kcal[key] * 1000.0

    fiber_density = density("fiber")
    if fiber_density is not None:
        target = fiber_target_density(goals)
        components["fiber"] = {
            "value": fiber_density,
            "score": 100.0 * _clamp01(fiber_density / target),
        }
    sugar_density = density("sugar")
    if sugar_density is not None:
        share = sugar_density / 1000.0 * SUGAR_KCAL_PER_G
        components["sugar"] = {"value": share, "score": _limit_score(share, SUGAR_ENERGY_LIMIT)}
    sat_density = density("saturated_fat")
    if sat_density is not None:
        share = sat_density / 1000.0 * FAT_KCAL_PER_G
        components["saturated_fat"] = {
            "value": share,
            "score": _limit_score(share, SATURATED_FAT_ENERGY_LIMIT),
        }
    salt_density = density("salt")
    if salt_density is not None:
        components["salt"] = {
            "value": salt_density,
            "score": _limit_score(salt_density, SALT_G_PER_1000KCAL_LIMIT),
        }

    if not components:
        result["reason"] = "insufficient_data"
        return result

    weight_sum = sum(WEIGHTS[key] for key in components)
    result["score"] = round(
        sum(WEIGHTS[key] * parts["score"] for key, parts in components.items()) / weight_sum
    )
    result["components"] = {
        key: {
            # Unrounded: the recommendations compare it with limits.
            "value": parts["value"],
            "score": round(parts["score"]),
            "weight": WEIGHTS[key],
        }
        for key, parts in components.items()
    }
    return result


def quality_item_from_entry(entry, category=None) -> dict:
    """The quality input for one logged ``MealItem``.

    The category is the entry's own snapshot (``basis["category"]``) when it
    names a real category; entries logged before snapshots carried it, or
    with the uninformative ``other``, use the product's current category
    (passed by the caller after one batched lookup).
    """
    basis = entry.basis if isinstance(entry.basis, dict) else {}
    snapshot = basis.get("category")
    # "other" says nothing about the food, so a category the user has set on
    # the product since then is better than the snapshot; a real category in
    # the snapshot is kept as logged.
    chosen = snapshot if snapshot not in (None, "other") else (category or snapshot)
    return {
        "name": entry.name,
        "category": chosen,
        "grams": entry.weight,
        "calories": entry.calories,
        "protein": entry.protein,
        "fat": entry.fat,
        "carbs": entry.carbs,
        "fiber": entry.fiber,
        "sugar": entry.sugar,
        "saturated_fat": entry.saturated_fat,
        "salt": entry.salt,
    }


def resolve_categories(entries) -> dict:
    """``{product_id: category}`` for entries whose snapshot has no real category.

    One query for any number of entries (none when every entry carries its
    category), so a year of days can be scored without a query per day.
    """
    missing = {
        entry.product_id
        for entry in entries
        if entry.product_id is not None
        and not (
            isinstance(entry.basis, dict)
            and entry.basis.get("category") not in (None, "other")
        )
    }
    if not missing:
        return {}

    from backend.app.models.nutrition.product import Product

    return dict(
        Product.query.filter(Product.id.in_(missing))
        .with_entities(Product.id, Product.category)
        .all()
    )


def quality_items(entries, categories=None) -> list[dict]:
    """Quality inputs for ``entries``.

    ``categories`` is the result of :func:`resolve_categories`; it is looked
    up here when the caller has not done it for a larger set.
    """
    entries = list(entries)
    if categories is None:
        categories = resolve_categories(entries)
    return [
        quality_item_from_entry(entry, categories.get(entry.product_id))
        for entry in entries
    ]
