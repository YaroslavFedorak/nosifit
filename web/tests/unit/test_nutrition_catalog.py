"""The system product catalog: dataset integrity and the idempotent seed."""

import csv
import json
import os

import pytest

from backend.app.extensions import db
from backend.app.models import Product, ProductName
from backend.app.utils.name_normalization import normalize_name
from web.scripts import seed_nutrition_products as seed
from web.scripts.nutrition_catalog import build_catalog

CATALOG_DIR = os.path.dirname(build_catalog.__file__)
REQUIRED = ("kcal", "protein", "fat", "carbs", "sugar", "fiber")


@pytest.fixture(scope="module")
def products():
    return seed.load_catalog()


def test_catalog_has_about_a_thousand_products(products):
    assert 950 <= len(products) <= 1200


def test_every_product_has_sourced_complete_values(products):
    for product in products:
        values = product["per_100g"]
        for name in REQUIRED:
            assert values[name] is not None, (product["key"], name)
            assert values[name] >= 0, (product["key"], name)
        assert values["kcal"] <= 950
        assert values["sugar"] <= values["carbs"] + 0.05, product["key"]
        if values["saturated_fat"] is not None:
            assert values["saturated_fat"] <= values["fat"] + 0.05, product["key"]
        source = product["source"]
        assert source["dataset"] in {
            "ciqual_2020", "usda_sr_legacy", "open_food_facts", "nosifit_recipe",
        }
        assert source["ref"], product["key"]


def test_products_have_names_in_every_locale_and_valid_units(products):
    for product in products:
        for locale in ("uk", "en", "pl", "ru"):
            assert product["names"][locale].strip(), (product["key"], locale)
        assert product["unit"] in {"g", "ml", "pcs"}
        assert product["grams_per_unit"] > 0
        assert product["category"] in build_catalog.CATEGORIES


def test_keys_and_names_are_unique(products):
    keys = [product["key"] for product in products]
    assert len(keys) == len(set(keys))
    for locale in ("uk", "en"):
        names = [normalize_name(product["names"][locale]) for product in products]
        assert len(names) == len(set(names)), locale


def test_catalog_covers_everyday_food_groups(products):
    counts = {}
    for product in products:
        counts[product["category"]] = counts.get(product["category"], 0) + 1
    for category in (
        "meat", "poultry", "fish", "seafood", "eggs", "dairy", "cheese", "grains",
        "pasta", "bread", "legumes", "vegetables", "fruits", "berries", "nuts",
        "seeds", "oils", "sauces", "prepared", "sweets", "beverages", "fast_food",
        "ingredients",
    ):
        assert counts.get(category, 0) >= 5, category


def test_recipes_only_use_catalog_products(products):
    keys = {product["key"] for product in products}
    recipes = [p for p in products if p["source"]["dataset"] == "nosifit_recipe"]
    assert recipes
    for product in recipes:
        for ingredient, grams in product["source"]["ingredients"]:
            assert ingredient in keys, (product["key"], ingredient)
            assert grams > 0
        # Typical home recipes are estimates; exact blends are not.
        assert product["verified"] == product["source"].get("exact", False)


def test_generated_json_matches_the_maintained_csv(products):
    with open(os.path.join(CATALOG_DIR, "catalog.csv"), encoding="utf-8") as handle:
        rows = [line for line in handle if line.strip() and not line.startswith("#")]
    csv_keys = [row["key"] for row in csv.DictReader(rows, delimiter=";")]
    assert csv_keys == [product["key"] for product in products], (
        "products.json is stale: rerun build_catalog.py"
    )


def test_label_products_are_documented(products):
    with open(os.path.join(CATALOG_DIR, "label_data.json"), encoding="utf-8") as handle:
        labels = json.load(handle)["products"]
    for product in products:
        if product["source"]["dataset"] == "open_food_facts":
            label = labels[product["source"]["ref"]]
            assert label["url"].startswith("https://world.openfoodfacts.org/product/")


def test_ciqual_value_parsing():
    assert build_catalog.parse_ciqual_value("12,5") == (12.5, False)
    assert build_catalog.parse_ciqual_value("traces") == (0.0, True)
    assert build_catalog.parse_ciqual_value("< 0,5") == (0.25, True)
    assert build_catalog.parse_ciqual_value("-") == (None, False)


def test_derivation_rules_never_invent_plant_values():
    values, derived = {"protein": 20.0, "fat": 5.0, "carbs": 0.0}, set()
    build_catalog.complete_values(values, derived, "meat", False)
    assert values["sugar"] == 0.0 and values["fiber"] == 0.0
    assert "kcal" in values  # EU factors

    values, derived = {"protein": 2.0, "fat": 0.5, "carbs": 10.0}, set()
    build_catalog.complete_values(values, derived, "vegetables", False)
    assert "sugar" not in values and "fiber" not in values
    with pytest.raises(build_catalog.CatalogError):
        build_catalog.check_values("veg", values, [])


def test_alcohol_counts_in_derived_energy():
    values, derived = {"protein": 0.4, "fat": 0.0, "carbs": 2.7, "fiber": 0.0, "alcohol": 3.9}, set()
    build_catalog.complete_values(values, derived, "beverages", False)
    assert values["kcal"] == pytest.approx(0.4 * 4 + 2.7 * 4 + 3.9 * 7, abs=0.1)


# --- seed --------------------------------------------------------------------


def _legacy_product(en, uk, kcal=165):
    product = Product(
        source="system", category="other", kcal_per_100g=kcal, protein_per_100g=31,
        fat_per_100g=3.6, carbs_per_100g=0, fiber_per_100g=0, default_unit="g",
        grams_per_unit=1, liquid_ml_per_100g=0,
    )
    product.names = [ProductName(locale="en", name=en), ProductName(locale="uk", name=uk)]
    db.session.add(product)
    db.session.commit()
    return product


def test_seed_is_idempotent_and_adopts_the_old_catalog(app, products):
    old_chicken = _legacy_product("Chicken breast", "Куряче філе")
    old_quinoa = _legacy_product("Quinoa, dry", "Кіноа суха", kcal=368)

    first = seed.seed_catalog(products)
    db.session.commit()
    assert first["created"] == len(products) - 1
    assert first["adopted"] == 1
    assert first["archived"] == 1

    second = seed.seed_catalog(products)
    db.session.commit()
    assert second == {
        "created": 0, "updated": 0, "unchanged": len(products), "adopted": 0, "archived": 0,
    }

    db.session.expire_all()
    chicken = db.session.get(Product, old_chicken.id)
    assert chicken.key == "chicken_breast_raw"
    assert chicken.data_source == "ciqual_2020" and chicken.source_ref
    assert chicken.sugar_per_100g == 0 and chicken.fiber_per_100g == 0
    assert {name.locale for name in chicken.names} == {"uk", "en", "pl", "ru"}
    assert db.session.get(Product, old_quinoa.id).is_active is False

    assert Product.query.filter(Product.owner_user_id.is_(None), Product.is_active).count() == len(products)
    assert ProductName.query.count() == 4 * len(products) + 2  # + the archived product


def test_seed_rolls_back_on_failure(app, products, monkeypatch):
    broken = [dict(products[0]), dict(products[0])]  # duplicate key

    with pytest.raises(Exception):
        seed.seed_catalog(broken)
        db.session.commit()
    db.session.rollback()
    assert Product.query.count() == 0
