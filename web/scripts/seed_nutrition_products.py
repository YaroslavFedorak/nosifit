"""Load the system product catalog (``nutrition_catalog/products.json``).

    python -m web.scripts.seed_nutrition_products

Idempotent and transaction-safe: products are upserted by their stable
``key`` in one transaction, so a second run changes nothing and a failed run
changes nothing at all. Values come only from the generated JSON; see
``nutrition_catalog/build_catalog.py`` for where they come from.

Products of the old hand-typed catalog (no ``key``) are adopted by their
English name, keeping their ids, so favorites and logged entries stay linked.
Logged entries are snapshots and never change. Old products without a
counterpart, and keys removed from the catalog, are archived, not deleted.
"""

from __future__ import annotations

import json
import os
from datetime import datetime

from sqlalchemy.orm import selectinload

from backend.app.extensions import db
from backend.app.models import Product, ProductName
from backend.app.utils.name_normalization import normalize_name

CATALOG_JSON = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "nutrition_catalog", "products.json"
)
LOCALES = ("uk", "en", "pl", "ru")

# Old catalog (English name) -> catalog key. Old products that are not listed
# here ("Quinoa, dry", "Americano", "Sports drink") have no sourced
# counterpart and are archived.
LEGACY_KEYS = {
    "Chicken breast": "chicken_breast_raw",
    "Chicken thigh": "chicken_thigh_skin_raw",
    "Turkey breast": "turkey_breast_raw",
    "Lean beef": "beef_rump_raw",
    "Lean pork": "pork_ham_raw",
    "Salmon": "salmon_raw",
    "Canned tuna": "tuna_canned_water",
    "Mackerel": "mackerel_raw",
    "Shrimp": "shrimp_cooked",
    "Egg": "egg_raw",
    "Egg white": "egg_white_raw",
    "Greek yogurt": "greek_yogurt_2",
    "Plain yogurt": "yogurt_plain_whole",
    "Cottage cheese 5%": "tvorog_5",
    "Cottage cheese 2%": "tvorog_0",
    "Hard cheese": "hard_cheese",
    "Mozzarella": "mozzarella",
    "Oatmeal": "oat_flakes",
    "White rice, dry": "rice_white_raw",
    "Brown rice, dry": "rice_brown_raw",
    "Buckwheat, dry": "buckwheat_raw",
    "Pasta, dry": "pasta_dry",
    "Whole wheat pasta": "pasta_whole_dry",
    "White bread": "bread_wheat",
    "Whole grain bread": "bread_whole_grain",
    "Wheat tortilla": "tortilla_wheat",
    "Potato": "potato_raw",
    "Sweet potato": "sweet_potato_raw",
    "Corn": "corn_canned",
    "Red kidney beans, cooked": "beans_red_cooked",
    "Chickpeas, cooked": "chickpeas_cooked",
    "Lentils, cooked": "lentils_cooked",
    "Broccoli": "broccoli",
    "Cauliflower": "cauliflower",
    "Spinach": "spinach",
    "Tomato": "tomato",
    "Cucumber": "cucumber",
    "Carrot": "carrot",
    "Bell pepper": "bell_pepper_red",
    "Avocado": "avocado",
    "Apple": "apple",
    "Banana": "banana",
    "Orange": "orange",
    "Strawberry": "strawberry",
    "Blueberries": "blueberry",
    "Raspberries": "raspberry",
    "Peanuts": "peanuts",
    "Almonds": "almonds",
    "Walnuts": "walnuts",
    "Peanut butter": "peanut_butter",
    "Olive oil": "olive_oil",
    "Honey": "honey",
    "Dark chocolate 70%": "chocolate_dark_70",
    "Black coffee": "coffee_black",
    "Espresso": "espresso",
    "Black tea": "tea_black",
    "Green tea": "tea_green",
    "Herbal tea": "tea_herbal",
    "Iced tea, sweetened": "iced_tea",
    "Milk 2.5%": "milk_25",
    "Milk 1.5%": "milk_15",
    "Kefir 2.5%": "kefir_25",
    "Ayran": "ayran",
    "Soy drink, unsweetened": "soy_drink",
    "Almond drink, unsweetened": "almond_drink",
    "Coconut water": "coconut_water",
    "Orange juice": "juice_orange",
    "Apple juice": "juice_apple",
    "Grape juice": "juice_grape",
    "Tomato juice": "juice_tomato",
    "Lemonade": "lemonade",
    "Cola": "cola",
    "Energy drink": "energy_drink",
    "Sparkling water": "water_sparkling",
    "Water": "water",
}

VALUE_FIELDS = {
    "kcal_per_100g": "kcal",
    "protein_per_100g": "protein",
    "fat_per_100g": "fat",
    "carbs_per_100g": "carbs",
    "sugar_per_100g": "sugar",
    "fiber_per_100g": "fiber",
    "saturated_fat_per_100g": "saturated_fat",
    "salt_per_100g": "salt",
}


def load_catalog(path=CATALOG_JSON):
    with open(path, encoding="utf-8") as handle:
        products = json.load(handle)["products"]
    keys = [item["key"] for item in products]
    if len(keys) != len(set(keys)):
        raise ValueError("products.json has duplicate keys")
    return products


def _apply(product, item) -> bool:
    """Copy catalog values onto ``product``; True if anything changed."""
    values = item["per_100g"]
    wanted = {
        "key": item["key"],
        "source": "system",
        "owner_user_id": None,
        "category": item["category"],
        "brand": item.get("brand"),
        "default_unit": item["unit"],
        "grams_per_unit": item["grams_per_unit"],
        "liquid_ml_per_100g": item["liquid_ml_per_100g"],
        "data_source": item["source"]["dataset"],
        "source_ref": str(item["source"]["ref"])[:64],
        "verified": bool(item["verified"]),
        "is_active": True,
        "normalized_name": normalize_name(item["names"]["uk"])[:160],
    }
    wanted.update({column: values[name] for column, name in VALUE_FIELDS.items()})

    changed = False
    for column, value in wanted.items():
        if getattr(product, column) != value:
            setattr(product, column, value)
            changed = True

    names = {name.locale: name for name in product.names}
    for locale in LOCALES:
        text = item["names"][locale]
        existing = names.get(locale)
        if existing is None:
            product.names.append(ProductName(locale=locale, name=text))
            changed = True
        elif existing.name != text or existing.normalized_name != normalize_name(text)[:160]:
            # Setting the name also refreshes normalized_name (model validator).
            existing.name = text
            changed = True
    return changed


def seed_catalog(products) -> dict:
    """Upsert ``products``; the caller commits. Returns counts."""
    system = (
        Product.query
        .options(selectinload(Product.names))
        .filter(Product.owner_user_id.is_(None))
        .all()
    )
    by_key = {product.key: product for product in system if product.key}
    legacy_by_en = {
        name.name: product
        for product in system
        if not product.key
        for name in product.names
        if name.locale == "en"
    }
    legacy_for_key = {
        key: legacy_by_en[en]
        for en, key in LEGACY_KEYS.items()
        if en in legacy_by_en
    }

    counts = {"created": 0, "updated": 0, "unchanged": 0, "adopted": 0, "archived": 0}
    seen = set()
    now = datetime.utcnow()

    for item in products:
        product = by_key.get(item["key"])
        if product is None and item["key"] in legacy_for_key:
            product = legacy_for_key[item["key"]]
            counts["adopted"] += 1
        if product is None:
            product = Product(created_at=now, updated_at=now)
            db.session.add(product)
            _apply(product, item)
            counts["created"] += 1
        elif _apply(product, item):
            product.updated_at = now
            counts["updated"] += 1
        else:
            counts["unchanged"] += 1
        seen.add(id(product))

    # Old products without a sourced counterpart, and keys dropped from the
    # catalog: archived so search no longer offers them; history keeps them.
    for product in system:
        if id(product) not in seen and product.is_active and product.source == "system":
            product.is_active = False
            product.updated_at = now
            counts["archived"] += 1

    db.session.flush()
    return counts


def seed_products(path=CATALOG_JSON) -> dict:
    """Run inside an app context; everything commits or nothing does."""
    from flask import has_app_context

    if not has_app_context():
        from web.app import create_app

        with create_app().app_context():
            return seed_products(path)

    products = load_catalog(path)
    try:
        counts = seed_catalog(products)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    print(
        "Nutrition catalog: {total} products — {created} created, {updated} updated, "
        "{unchanged} unchanged ({adopted} adopted from the old catalog), "
        "{archived} archived".format(total=len(products), **counts)
    )
    return counts


if __name__ == "__main__":
    seed_products()
