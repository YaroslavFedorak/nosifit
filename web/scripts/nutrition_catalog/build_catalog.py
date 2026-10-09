"""Build ``products.json`` (the system product catalog) from official sources.

Developer tool; the app and the seed only read the generated JSON.

    python -m web.scripts.nutrition_catalog.build_catalog \\
        --usda path/to/FoodData_Central_sr_legacy_food_csv_2018-04 \\
        --ciqual "path/to/Table Ciqual 2020_ENG_2020 07 07.xls"

Sources (not committed; download them to rebuild):

* USDA FoodData Central, SR Legacy (April 2018), public domain (CC0):
  https://fdc.nal.usda.gov/download-datasets
* ANSES CIQUAL French food composition table 2020, Etalab Open Licence 2.0:
  https://ciqual.anses.fr/  (the .xls needs ``pip install xlrd``; a CSV
  export of the same sheet works too)

``catalog.csv`` lists every product: its key, category, names in four
languages, default unit and the source row its values come from (``usda`` /
``ciqual`` + id, ``label`` + barcode in ``label_data.json`` (manufacturer
label values from Open Food Facts, for Ukrainian products the composition
tables lack), or ``recipe`` + a key in ``recipes.json``). An optional
``fallback`` source fills nutrients the primary source does not report.

Conventions (shared by everything the app calculates):

* every value is per 100 g of edible product;
* ``carbs`` are available carbohydrates (EU labelling convention, as in
  CIQUAL). USDA's carbohydrate "by difference" includes fiber, so fiber is
  subtracted from it;
* ``kcal`` is the source's energy value. CIQUAL's EU 1169/2011 column is
  used; when it is missing, energy is computed with the same EU factors
  (4 protein, 4 carbs, 9 fat, 2 fiber, 7 alcohol, 2.4 polyols, 3 organic
  acids) and the field is marked derived.

Rules for values a source leaves out (each use is recorded in ``derived``):

* CIQUAL "traces" = 0; "< x" (below the quantification limit) = x / 2,
  or 0 for rows flagged ``loq_zero`` (pure fats);
* sugar = 0 when carbs are ≤ 0.1 g (sugars are part of carbs);
* fiber = 0 for foods of animal origin without plant ingredients
  (dietary fiber exists only in plants), also when the lab reported it as
  "< LOQ";
* saturated fat = 0 when fat is ≤ 0.1 g;
* salt from USDA sodium: salt = sodium × 2.5;
* sugar slightly above carbs (separate analyses, "< LOQ" halves) is capped
  at carbs; more than 1 g above is an error;
* ``liquid = water`` takes hydration from the source's water content.

``verified`` is true for values taken from a source row (or an exact blend of
such rows) and false for dishes calculated from a typical home recipe, which
are estimates: real portions and cooking losses vary.

Anything else missing for kcal / protein / fat / carbs / sugar / fiber is an
error: pick another source row or add a fallback. Nothing is estimated.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from dataclasses import dataclass, field

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG_CSV = os.path.join(HERE, "catalog.csv")
RECIPES_JSON = os.path.join(HERE, "recipes.json")
LABELS_JSON = os.path.join(HERE, "label_data.json")
OUTPUT_JSON = os.path.join(HERE, "products.json")

NUTRIENTS = ("kcal", "protein", "fat", "carbs", "sugar", "fiber", "saturated_fat", "salt")
REQUIRED = ("kcal", "protein", "fat", "carbs", "sugar", "fiber")

CATEGORIES = {
    "meat", "poultry", "fish", "seafood", "eggs", "dairy", "cheese",
    "grains", "pasta", "bread", "legumes", "vegetables", "fruits", "berries",
    "nuts", "seeds", "oils", "sauces", "prepared", "fast_food", "sweets",
    "snacks", "beverages", "ingredients", "other",
}
# Fiber is 0 by definition for these unless the row says it has plant parts.
ANIMAL_CATEGORIES = {"meat", "poultry", "fish", "seafood", "eggs"}
UNITS = {"g", "ml", "pcs"}
LOCALES = ("uk", "en", "pl", "ru")

USDA_NUTRIENTS = {
    "1008": "kcal",
    "1003": "protein",
    "1004": "fat",
    "1005": "carbs",
    "2000": "sugar",
    "1063": "sugar_nlea",
    "1079": "fiber",
    "1258": "saturated_fat",
    "1093": "sodium_mg",
    "1051": "water",
    "1018": "alcohol",
}

CIQUAL_COLUMNS = {
    "kcal": "Energy, Regulation EU No 1169/2011 (kcal/100g)",
    "protein": "Protein (g/100g)",
    "fat": "Fat (g/100g)",
    "carbs": "Carbohydrate (g/100g)",
    "sugar": "Sugars (g/100g)",
    "fiber": "Fibres (g/100g)",
    "saturated_fat": "FA saturated (g/100g)",
    "salt": "Salt (g/100g)",
    "water": "Water (g/100g)",
    "alcohol": "Alcohol (g/100g)",
    "polyols": "Polyols (g/100g)",
    "organic_acids": "Organic acids (g/100g)",
}

# Energy conversion factors of Regulation (EU) 1169/2011, Annex XIV (kcal/g).
EU_ENERGY_FACTORS = {
    "protein": 4,
    "carbs": 4,
    "fat": 9,
    "fiber": 2,
    "alcohol": 7,
    "polyols": 2.4,
    "organic_acids": 3,
}


class CatalogError(Exception):
    pass


@dataclass
class SourceValues:
    dataset: str
    ref: str
    description: str
    values: dict
    derived: set = field(default_factory=set)


# --- sources ---------------------------------------------------------------

def load_usda(directory):
    def rows(name):
        with open(os.path.join(directory, name), encoding="utf-8") as handle:
            yield from csv.DictReader(handle)

    foods = {row["fdc_id"]: row["description"] for row in rows("food.csv")}
    values = {fdc_id: {} for fdc_id in foods}
    for row in rows("food_nutrient.csv"):
        key = USDA_NUTRIENTS.get(row["nutrient_id"])
        if key and row["fdc_id"] in values and row["amount"] != "":
            values[row["fdc_id"]][key] = float(row["amount"])
    return {fdc_id: (foods[fdc_id], values[fdc_id]) for fdc_id in foods}


def _ciqual_rows(path):
    if path.lower().endswith(".xls"):
        try:
            import xlrd  # noqa: PLC0415 - optional, developer-only dependency
        except ImportError as exc:
            raise CatalogError("Reading the CIQUAL .xls needs: pip install xlrd") from exc
        sheet = xlrd.open_workbook(path).sheet_by_index(0)
        header = [str(value).strip() for value in sheet.row_values(0)]
        for index in range(1, sheet.nrows):
            yield dict(zip(header, (str(value) for value in sheet.row_values(index))))
    else:
        with open(path, encoding="utf-8") as handle:
            yield from csv.DictReader(handle)


def parse_ciqual_value(raw):
    """``(value, approximate)``; value None when not reported."""
    text = (raw or "").strip().replace(",", ".")
    if text in ("", "-"):
        return None, False
    if text.lower() == "traces":
        return 0.0, True
    if text.startswith("<"):
        return round(float(text[1:].strip()) / 2, 3), True
    return float(text), False


def load_ciqual(path):
    table = {}
    for row in _ciqual_rows(path):
        code = row["alim_code"].strip().split(".")[0]
        values, approximate = {}, set()
        for key, column in CIQUAL_COLUMNS.items():
            value, approx = parse_ciqual_value(row.get(column))
            if value is not None:
                values[key] = value
                if approx:
                    approximate.add(key)
        table[code] = (row["alim_nom_eng"].strip(), values, approximate)
    return table


def usda_values(usda, ref):
    if ref not in usda:
        raise CatalogError(f"usda:{ref} does not exist")
    description, raw = usda[ref]
    values, derived = {}, set()
    for key in ("kcal", "protein", "fat", "saturated_fat", "water", "alcohol"):
        if key in raw:
            values[key] = raw[key]
    sugar = raw.get("sugar", raw.get("sugar_nlea"))
    if sugar is not None:
        values["sugar"] = sugar
    if "fiber" in raw:
        values["fiber"] = raw["fiber"]
    if "carbs" in raw:
        # Carbohydrate by difference includes fiber; store available carbs.
        values["carbs"] = max(raw["carbs"] - raw.get("fiber", 0.0), 0.0)
        if raw.get("fiber"):
            derived.add("carbs:usda_minus_fiber")
    if "sodium_mg" in raw:
        values["salt"] = round(raw["sodium_mg"] * 2.5 / 1000, 3)
        derived.add("salt:from_sodium")
    return SourceValues("usda_sr_legacy", ref, description, values, derived)


def ciqual_values(ciqual, ref):
    if ref not in ciqual:
        raise CatalogError(f"ciqual:{ref} does not exist")
    description, values, approximate = ciqual[ref]
    derived = {f"{key}:below_quantification_limit" for key in approximate}
    return SourceValues("ciqual_2020", ref, description, dict(values), derived)


def label_values(labels, ref):
    product = labels.get(ref)
    if product is None:
        raise CatalogError(f"label:{ref} is not in label_data.json")
    values = {name: value for name, value in product["per_100g"].items() if value is not None}
    description = f"{product['product_name']} ({product['brand']}), {product['url']}"
    return SourceValues("open_food_facts", ref, description, values)


def source_values(spec, usda, ciqual, labels=None):
    dataset, _, ref = spec.partition(":")
    if dataset == "usda":
        return usda_values(usda, ref)
    if dataset == "ciqual":
        return ciqual_values(ciqual, ref)
    if dataset == "label":
        return label_values(labels or {}, ref)
    raise CatalogError(f"unknown source {spec!r}")


# --- derivation and checks ---------------------------------------------------

def complete_values(values, derived, category, fiber_free, loq_zero=False):
    # Pure fats and similar: a "< LOQ" protein or carb trace is 0, not LOQ/2.
    if loq_zero:
        for item in sorted(derived):
            name, _, rule = item.partition(":")
            if rule == "below_quantification_limit":
                values[name] = 0.0
                derived.discard(item)
                derived.add(f"{name}:zero_below_quantification_limit")
    # "< LOQ" fiber in fish or meat is a lab limit, not fiber: it is 0.
    if (category in ANIMAL_CATEGORIES or fiber_free) and "fiber:below_quantification_limit" in derived:
        values.pop("fiber", None)
        derived.discard("fiber:below_quantification_limit")
    if "sugar" not in values and values.get("carbs") is not None and values["carbs"] <= 0.1:
        values["sugar"] = 0.0
        derived.add("sugar:zero_carbs")
    if "fiber" not in values and (category in ANIMAL_CATEGORIES or fiber_free):
        values["fiber"] = 0.0
        derived.add("fiber:animal_origin")
    if "saturated_fat" not in values and values.get("fat") is not None and values["fat"] <= 0.1:
        values["saturated_fat"] = 0.0
        derived.add("saturated_fat:zero_fat")
    if "kcal" not in values and all(k in values for k in ("protein", "fat", "carbs", "fiber")):
        # Alcohol, polyols and organic acids count too (beer, wine, sugar-free
        # sweets); a missing value for them means none.
        values["kcal"] = round(
            sum(factor * values.get(name, 0.0) for name, factor in EU_ENERGY_FACTORS.items()),
            1,
        )
        derived.add("kcal:eu_factors")

    # A part never exceeds its whole. "< LOQ" halves can exceed a tiny
    # whole, and separately analysed sugars can exceed carbohydrate by
    # difference by a little: cap at carbs, and say so.
    if values.get("sugar") is not None and values.get("carbs") is not None:
        if values["sugar"] > values["carbs"]:
            if values["sugar"] - values["carbs"] > 1.0:
                raise CatalogError(
                    f"sugar {values['sugar']} far above carbs {values['carbs']}"
                )
            values["sugar"] = values["carbs"]
            derived.add("sugar:capped_at_carbs")
    if values.get("saturated_fat") is not None and values.get("fat") is not None:
        if values["saturated_fat"] > values["fat"] and any(
            item.startswith("saturated_fat:") for item in derived
        ):
            values["saturated_fat"] = values["fat"]


def check_values(key, values, warnings):
    missing = [name for name in REQUIRED if values.get(name) is None]
    if missing:
        raise CatalogError(f"{key}: missing {', '.join(missing)}")
    for name, value in values.items():
        if value is not None and value < 0:
            raise CatalogError(f"{key}: negative {name}")
    if values["kcal"] > 950 or values["protein"] > 100 or values["fat"] > 100 or values["carbs"] > 100:
        raise CatalogError(f"{key}: value out of range {values}")
    if values["sugar"] > values["carbs"] + 0.05:
        raise CatalogError(f"{key}: sugar {values['sugar']} > carbs {values['carbs']}")
    if values.get("saturated_fat") is not None and values["saturated_fat"] > values["fat"] + 0.05:
        raise CatalogError(f"{key}: saturated fat > fat")

    # Energy plausibility. Sources use their own factors (USDA: specific
    # Atwater factors), so a difference only warns.
    computed = sum(factor * (values.get(name) or 0.0) for name, factor in EU_ENERGY_FACTORS.items())
    if abs(values["kcal"] - computed) > max(20.0, 0.15 * values["kcal"]):
        warnings.append(f"{key}: kcal {values['kcal']} vs macros {computed:.0f}")


def round_values(values):
    digits = {"kcal": 1, "salt": 3}
    return {
        name: (None if values.get(name) is None else round(values[name], digits.get(name, 2)))
        for name in NUTRIENTS
    }


# --- catalog -----------------------------------------------------------------

def read_catalog(path=CATALOG_CSV):
    with open(path, encoding="utf-8") as handle:
        lines = [line for line in handle if line.strip() and not line.lstrip().startswith("#")]
    reader = csv.DictReader(lines, delimiter=";")
    rows = []
    for number, row in enumerate(reader, start=2):
        row = {name: (value or "").strip() for name, value in row.items() if name}
        row["_line"] = number
        rows.append(row)
    return rows


def validate_row(row, seen_keys, seen_names):
    key = row["key"]
    where = f"line {row['_line']} ({key})"
    if not key or not key.replace("_", "").isalnum() or key != key.lower():
        raise CatalogError(f"{where}: key must be lowercase snake_case")
    if key in seen_keys:
        raise CatalogError(f"{where}: duplicate key")
    seen_keys.add(key)
    if row["category"] not in CATEGORIES:
        raise CatalogError(f"{where}: unknown category {row['category']!r}")
    if row["unit"] not in UNITS:
        raise CatalogError(f"{where}: unknown unit {row['unit']!r}")
    for locale in LOCALES:
        name = row[locale]
        if not name:
            raise CatalogError(f"{where}: missing {locale} name")
        folded = (locale, name.casefold())
        if folded in seen_names:
            raise CatalogError(f"{where}: duplicate {locale} name {name!r}")
        seen_names.add(folded)
    if float(row["grams_per_unit"]) <= 0:
        raise CatalogError(f"{where}: grams_per_unit must be positive")


def build(usda_dir, ciqual_path, output=OUTPUT_JSON):
    usda = load_usda(usda_dir)
    ciqual = load_ciqual(ciqual_path)
    with open(RECIPES_JSON, encoding="utf-8") as handle:
        recipes = json.load(handle)
    with open(LABELS_JSON, encoding="utf-8") as handle:
        labels = json.load(handle)["products"]

    rows = read_catalog()
    seen_keys, seen_names = set(), set()
    for row in rows:
        validate_row(row, seen_keys, seen_names)

    built, warnings, by_key = [], [], {}

    def build_row(row):
        key = row["key"]
        flags = set(filter(None, row.get("flags", "").split(",")))
        if row["source"] == "recipe":
            values, derived, source = recipe_values(row, recipes, by_key)
        else:
            primary = source_values(f"{row['source']}:{row['source_id']}", usda, ciqual, labels)
            values, derived = dict(primary.values), set(primary.derived)
            source = {
                "dataset": primary.dataset,
                "ref": primary.ref,
                "description": primary.description,
            }
            for spec in filter(None, row.get("fallback", "").split(",")):
                fallback = source_values(spec, usda, ciqual, labels)
                for name, value in fallback.values.items():
                    if name not in values:
                        values[name] = value
                        derived.add(f"{name}:from_{fallback.dataset}_{fallback.ref}")
        complete_values(
            values, derived, row["category"], "fiber_free" in flags, "loq_zero" in flags
        )
        check_values(key, values, warnings)
        water = values.get("water")
        liquid = row.get("liquid") or "0"
        if liquid == "water":
            # Hydration from the source's water content (g of water ≈ ml).
            if water is None:
                raise CatalogError(f"{key}: liquid=water but the source has no water value")
            liquid = round(water, 1)
        return {
            "_water": water,
            "key": key,
            "category": row["category"],
            "names": {locale: row[locale] for locale in LOCALES},
            "unit": row["unit"],
            "grams_per_unit": float(row["grams_per_unit"]),
            "liquid_ml_per_100g": float(liquid),
            "brand": row.get("brand") or None,
            "per_100g": round_values(values),
            "source": source,
            "verified": source["dataset"] != "nosifit_recipe" or source.get("exact", False),
            "derived": sorted(derived),
        }

    # Plain products first: recipes are built from them. Every problem is
    # reported at once, then the build fails.
    errors = []
    for row in sorted(rows, key=lambda item: item["source"] == "recipe"):
        try:
            product = build_row(row)
        except CatalogError as exc:
            errors.append(str(exc))
            continue
        by_key[product["key"]] = product
    if errors:
        raise CatalogError("\n".join(errors))
    built = [
        {name: value for name, value in by_key[row["key"]].items() if not name.startswith("_")}
        for row in rows
    ]

    with open(output, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(
            {
                "version": 1,
                "basis": "per 100 g edible portion; carbs = available carbohydrates",
                "sources": {
                    # Attribution and licence terms: see SOURCES.md.
                    "usda_sr_legacy": "USDA ARS, FoodData Central SR Legacy, 2018-04 (CC0 1.0)",
                    "ciqual_2020": "Anses. 2020. Ciqual French food composition table, updated 2020-07-07, "
                                   "https://ciqual.anses.fr/ (Licence Ouverte / Etalab 2.0); "
                                   "derived values marked in 'derived' are NosiFit's",
                    "open_food_facts": "Open Food Facts contributors, https://world.openfoodfacts.org/ "
                                       "(ODbL 1.0 / DbCL 1.0), extract in label_data.json",
                    "nosifit_recipe": "Calculated from the listed catalog ingredients",
                },
                "products": built,
            },
            handle,
            ensure_ascii=False,
            indent=1,
        )
        handle.write("\n")
    return built, warnings


def recipe_values(row, recipes, by_key):
    key = row["source_id"]
    recipe = recipes.get(key)
    if recipe is None:
        raise CatalogError(f"{row['key']}: recipe {key!r} not in recipes.json")
    total_raw = 0.0
    sums = {name: 0.0 for name in NUTRIENTS + ("water",)}
    unknown = set()
    for ingredient, grams in recipe["ingredients"]:
        product = by_key.get(ingredient)
        if product is None:
            raise CatalogError(f"{row['key']}: ingredient {ingredient!r} is not a catalog product")
        total_raw += grams
        for name in NUTRIENTS + ("water",):
            value = product["per_100g"].get(name) if name != "water" else product.get("_water")
            if value is None:
                unknown.add(name)
            else:
                sums[name] += value * grams / 100
    cooked = recipe.get("cooked_weight_g", total_raw)
    values = {
        name: sums[name] / cooked * 100
        for name in NUTRIENTS + ("water",)
        if name not in unknown
    }
    source = {
        "dataset": "nosifit_recipe",
        "ref": key,
        "description": recipe.get("note", ""),
        "ingredients": recipe["ingredients"],
        "cooked_weight_g": cooked,
        # Exact compositions (a blend of two milks, milled oats) are as
        # reliable as their ingredients; typical home recipes are estimates.
        "exact": bool(recipe.get("exact")),
    }
    return values, {"recipe"}, source


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--usda", required=True, help="SR Legacy CSV directory")
    parser.add_argument("--ciqual", required=True, help="CIQUAL 2020 .xls (or CSV export)")
    parser.add_argument("--output", default=OUTPUT_JSON)
    args = parser.parse_args(argv)
    try:
        built, warnings = build(args.usda, args.ciqual, args.output)
    except CatalogError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    for warning in warnings:
        print(f"warning: {warning}")
    counts = {}
    for product in built:
        counts[product["category"]] = counts.get(product["category"], 0) + 1
    print(f"{len(built)} products -> {args.output}")
    for category, count in sorted(counts.items()):
        print(f"  {category}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
