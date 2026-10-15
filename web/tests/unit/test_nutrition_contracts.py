"""What the nutrition code promises to its consumers: translations, API shapes,
imports and the goal-history migration."""
import json
import os
import re
import secrets
from pathlib import Path

import pytest
from flask_migrate import downgrade, upgrade
from sqlalchemy import create_engine, inspect, text

from backend.app.services.nutrition import recommendation_service
from backend.app.services.nutrition.barcode_service import normalize_external_product
from backend.app.services.nutrition.product_service import (
    ProductServiceError,
    create_user_product,
)
from web.app import create_app
from web.tests import conftest

ROOT = Path(__file__).resolve().parents[3]
LANGUAGES = ("uk", "en", "pl", "ru")


def translations(language):
    return json.loads((ROOT / "shared" / "translations" / language / "nutrition.json").read_text("utf-8"))


def dig(tree, dotted):
    for part in dotted.split("."):
        tree = tree[part]
    return tree


def placeholders(text_):
    return set(re.findall(r"\{(\w+)\}", text_))


# --- translations ----------------------------------------------------------

def emitted_keys():
    source = Path(recommendation_service.__file__).read_text("utf-8")
    return sorted(set(re.findall(r'"(recommendations\.items\.[a-z_.]+)"', source)))


def test_the_rules_emit_a_known_set_of_keys():
    keys = emitted_keys()
    assert len(keys) >= 20
    assert "recommendations.items.salt.high.message" in keys
    assert "recommendations.items.fiber.low.title" in keys
    assert "recommendations.items.hydration.low.message" in keys


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_recommendation_has_text_in_every_language(language):
    tree = translations(language)
    for key in emitted_keys():
        value = dig(tree, key)
        assert isinstance(value, str) and value.strip(), (language, key)


def test_translated_messages_use_the_same_parameters_in_every_language():
    reference = translations("en")
    for key in emitted_keys():
        expected = placeholders(dig(reference, key))
        for language in LANGUAGES:
            assert placeholders(dig(translations(language), key)) == expected, (language, key)


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_calorie_status_has_a_label(language):
    labels = translations(language)["balance"]["status"]
    assert {"over", "under", "normal", "unavailable", "no_data"} <= set(labels)
    assert all(isinstance(v, str) and v for v in labels.values())


# --- API shapes the clients rely on ---------------------------------------

def test_the_day_response_keeps_every_field_the_page_reads(app, user, client):
    client.post("/auth/login", data={"email": user.email, "password": "password123"})
    body = client.get("/api/nutrition/day").get_json()
    for key in ("kcal", "kcal_goal", "kcal_percent", "kcal_balance", "balance_status", "protein", "protein_goal",
                "protein_percent", "fat", "fat_goal", "carb", "carb_goal", "fiber", "fiber_goal", "sugar",
                "water", "water_goal", "water_percent", "meals", "goals", "macros_ratio", "quality",
                "kcal_diff_label", "protein_diff_label", "fat_diff_label", "carb_diff_label",
                "current_weight", "progress", "kcal_yesterday"):
        assert key in body, key
    # No profile: targets are absent, said so explicitly, and nothing claims to be "over".
    assert body["goals_available"] is False and body["balance_status"] == "unavailable"
    assert body["water_goal"] is None


def test_the_stats_response_keeps_its_keys(app, user, client):
    client.post("/auth/login", data={"email": user.email, "password": "password123"})
    body = client.get("/api/nutrition/stats").get_json()
    assert {"kcal", "weight", "avg_kcal", "goal_kcal", "current_weight", "weight_trend"} <= set(body)
    assert set(body["kcal"]) >= {"labels", "values"} and set(body["weight"]) == {"labels", "values"}


def test_the_dashboard_exposes_real_water(app, user, client):
    client.post("/auth/login", data={"email": user.email, "password": "password123"})
    client.post("/api/nutrition/water", json={"amount": 0.7})
    today = client.get("/api/dashboard/today").get_json()
    assert today["nutrition"]["water"] == 0.7


# --- imports and user products: energy arithmetic is not a gate ------------

def off(**nutriments):
    base = {"energy-kcal_100g": 100, "proteins_100g": 5, "fat_100g": 2, "carbohydrates_100g": 15}
    base.update(nutriments)
    base = {key: value for key, value in base.items() if value is not None}   # None = leave it out
    return {"code": "5449000000996", "product_name": "Thing", "lang": "en", "quantity": "100 g",
            "product_quantity_unit": "g", "nutriments": base}


def test_declared_energy_far_from_the_macro_arithmetic_is_a_warning_not_a_refusal():
    # Erythritol: all carbohydrate, no energy.
    sweetener = normalize_external_product(off(**{"energy-kcal_100g": 0, "proteins_100g": 0, "fat_100g": 0,
                                                  "carbohydrates_100g": 99.5, "sugars_100g": 0}), "en")
    assert sweetener["importable"] is True and sweetener["invalid"] == {}
    assert "energy_mismatch" in sweetener["warnings"] and sweetener["kcal_per_100g"] == 0

    # Polyol sweets: about 2.4 kcal/g instead of 4.
    polyols = normalize_external_product(off(**{"energy-kcal_100g": 215, "proteins_100g": 0, "fat_100g": 0,
                                                "carbohydrates_100g": 90}), "en")
    assert polyols["importable"] is True and "energy_mismatch" in polyols["warnings"]

    # Even a value that is plainly off is shown for the user to check.
    odd = normalize_external_product(off(**{"energy-kcal_100g": 10}), "en")
    assert odd["importable"] is True and "energy_mismatch" in odd["warnings"] and odd["kcal_per_100g"] == 10

    # Energy that fits the macros has no warning.
    fine = normalize_external_product(off(), "en")
    assert "energy_mismatch" not in fine["warnings"]


def test_physical_impossibilities_are_still_refused():
    heavy = normalize_external_product(off(proteins_100g=40, fat_100g=40, carbohydrates_100g=40), "en")
    assert heavy["importable"] is False and heavy["invalid"]["protein_per_100g"] == "macros_exceed_100g"
    sugar = normalize_external_product(off(**{"sugars_100g": 40}), "en")
    assert sugar["invalid"]["sugar_per_100g"] == "exceeds_carbs"


def test_units_are_converted_not_mixed():
    kj = normalize_external_product(off(**{"energy-kcal_100g": None, "energy-kj_100g": 418.4}), "en")
    assert kj["kcal_per_100g"] == pytest.approx(100, abs=0.01) and "energy_from_kj" in kj["warnings"]
    sodium = normalize_external_product(off(**{"salt_100g": None, "sodium_100g": 0.4}), "en")
    assert sodium["salt_per_100g"] == pytest.approx(1.0) and "salt_from_sodium" in sodium["warnings"]
    missing = normalize_external_product(off(**{"fiber_100g": None}), "en")
    assert missing["fiber_per_100g"] is None   # unknown, not 0


def test_a_user_product_with_unusual_energy_is_accepted(app, user):
    wine = create_user_product(user.id, {
        "name": "Dessert wine", "kcal_per_100g": 140, "protein_per_100g": 0, "fat_per_100g": 0,
        "carbs_per_100g": 8, "default_unit": "ml", "grams_per_unit": 1.0, "category": "beverages",
    })
    assert wine["kcal_per_100g"] == 140   # alcohol carries energy the macros do not show


@pytest.mark.parametrize("field, value", [
    ("kcal_per_100g", float("nan")), ("kcal_per_100g", float("inf")), ("protein_per_100g", -1),
    ("fat_per_100g", "abc"), ("carbs_per_100g", 100.01), ("kcal_per_100g", 951),
])
def test_a_user_product_with_impossible_values_is_refused(app, user, field, value):
    data = {"name": "Thing", "kcal_per_100g": 100, "protein_per_100g": 5, "fat_per_100g": 2,
            "carbs_per_100g": 15, "default_unit": "g", "grams_per_unit": 1.0}
    data[field] = value
    with pytest.raises(ProductServiceError):
        create_user_product(user.id, data)


def test_optional_nutrients_stay_unknown_when_left_blank(app, user):
    product = create_user_product(user.id, {
        "name": "Homemade", "kcal_per_100g": 100, "protein_per_100g": 5, "fat_per_100g": 2,
        "carbs_per_100g": 15, "default_unit": "g", "grams_per_unit": 1.0, "fiber_per_100g": "",
    })
    assert product["fiber_per_100g"] is None and product["sugar_per_100g"] is None
    assert product["salt_per_100g"] is None
    zero = create_user_product(user.id, {
        "name": "Homemade zero", "kcal_per_100g": 100, "protein_per_100g": 5, "fat_per_100g": 2,
        "carbs_per_100g": 15, "default_unit": "g", "grams_per_unit": 1.0, "fiber_per_100g": 0,
    })
    assert zero["fiber_per_100g"] == 0


# --- the goal-history migration -------------------------------------------

PREVIOUS = "c5e1d7a9b3f2"
THIS = "b7d2e4a8c1f6"


def migrated_app(schema):
    uri = conftest.TEST_DATABASE_URI.replace(conftest.TEST_SCHEMA, schema)
    return create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": uri}), uri


@pytest.fixture
def scratch_schema():
    name = f"mig_{os.getpid()}_{secrets.token_hex(3)}"
    engine = create_engine(conftest._BASE_DATABASE_URI)
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public"))
        connection.execute(text(f'CREATE SCHEMA "{name}"'))
    yield name
    with engine.begin() as connection:
        connection.execute(text(f'DROP SCHEMA "{name}" CASCADE'))
    engine.dispose()


def test_the_goal_history_migration_keeps_existing_data_and_reverses(scratch_schema):
    app, uri = migrated_app(scratch_schema)
    directory = str(ROOT / "migrations")
    engine = create_engine(uri)
    try:
        with app.app_context():
            upgrade(directory=directory, revision=PREVIOUS)
        with engine.begin() as connection:
            assert "nutrition_goal_history" not in inspect(connection).get_table_names(schema=scratch_schema)
            connection.execute(text(
                "INSERT INTO users (username, email, password, created_at, updated_at) "
                "VALUES ('legacy', 'legacy@example.com', 'x', now(), now())"))
            connection.execute(text(
                "INSERT INTO user_goals (user_id, calories_goal, protein_goal, fat_goal, carb_goal, fiber_goal) "
                "SELECT id, 2200, 140, 70, 250, 30 FROM users"))

        with app.app_context():
            upgrade(directory=directory)
        with engine.begin() as connection:
            tables = inspect(connection).get_table_names(schema=scratch_schema)
            assert "nutrition_goal_history" in tables
            # Nothing is copied or invented for existing users.
            assert connection.execute(text("SELECT count(*) FROM nutrition_goal_history")).scalar() == 0
            assert connection.execute(text("SELECT calories_goal FROM user_goals")).scalar() == 2200
            assert connection.execute(text("SELECT count(*) FROM users")).scalar() == 1

        with app.app_context():
            downgrade(directory=directory, revision=PREVIOUS)
        with engine.begin() as connection:
            assert "nutrition_goal_history" not in inspect(connection).get_table_names(schema=scratch_schema)
            assert connection.execute(text("SELECT calories_goal FROM user_goals")).scalar() == 2200

        with app.app_context():
            upgrade(directory=directory)           # and forward again
        with engine.begin() as connection:
            assert "nutrition_goal_history" in inspect(connection).get_table_names(schema=scratch_schema)
    finally:
        engine.dispose()
