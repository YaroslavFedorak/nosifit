"""API-level checks for the nutrition module (validation, meal categories,
water corrections) and the translation fallback."""

from datetime import date, timedelta

from backend.app.extensions import db
from backend.app.models import Meal, MealItem, Product, ProductName
from backend.app.services.nutrition.meal_categories import normalize_meal_category
from backend.app.services.nutrition.meal_service import copy_meal_service
from web.app.i18n.locale import load_translation


def login(client):
    return client.post(
        "/auth/login",
        data={"email": "test@example.com", "password": "password123"},
    )


def make_product(kcal=100, liquid=0, unit="g", grams_per_unit=1):
    product = Product(
        source="system",
        kcal_per_100g=kcal,
        protein_per_100g=1,
        fat_per_100g=1,
        carbs_per_100g=1,
        fiber_per_100g=0,
        default_unit=unit,
        grams_per_unit=grams_per_unit,
        liquid_ml_per_100g=liquid,
    )
    db.session.add(product)
    db.session.flush()
    db.session.add(ProductName(product_id=product.id, locale="uk", name="Тест"))
    db.session.commit()
    return product


def test_meal_category_aliases():
    assert normalize_meal_category("breakfast") == "breakfast"
    assert normalize_meal_category("Сніданок") == "breakfast"
    assert normalize_meal_category(" обід ") == "lunch"
    assert normalize_meal_category("Kolacja") == "dinner"
    assert normalize_meal_category("Перекус") == "snack"
    assert normalize_meal_category("brunch") is None
    assert normalize_meal_category(None) is None


def test_create_meal_stores_category_key(app, client, user):
    login(client)

    response = client.post("/api/nutrition/meals", json={"category": "Сніданок"})
    assert response.status_code == 201
    assert response.get_json()["category"] == "breakfast"
    assert response.get_json()["name"] == "breakfast"

    response = client.post("/api/nutrition/meals", json={"category": "brunch"})
    assert response.status_code == 400
    assert response.get_json()["code"] == "invalid_category"


def test_legacy_meal_is_serialized_with_key(app, client, user):
    login(client)
    with app.app_context():
        db.session.add(Meal(user_id=user.id, date=date.today(), name="Вечеря", category="Вечеря"))
        db.session.commit()

    meals = client.get("/api/nutrition/day").get_json()["meals"]
    assert meals[0]["category"] == "dinner"


def test_edit_meal_category(app, client, user):
    login(client)
    meal_id = client.post("/api/nutrition/meals", json={"category": "lunch"}).get_json()["id"]

    response = client.put(f"/api/nutrition/meals/{meal_id}", json={"category": "snack", "time": "16:30"})
    assert response.status_code == 200
    assert response.get_json()["category"] == "snack"
    assert response.get_json()["time"] == "16:30"

    response = client.put(f"/api/nutrition/meals/{meal_id}", json={"category": "???"})
    assert response.status_code == 400


def test_entry_amount_limits(app, client, user):
    login(client)
    with app.app_context():
        product_id = make_product().id
    meal_id = client.post("/api/nutrition/meals", json={"category": "lunch"}).get_json()["id"]

    too_much = client.post(
        "/api/nutrition/entries/bulk",
        json={"meal_id": meal_id, "items": [{"product_id": product_id, "amount": 50000, "unit": "g"}]},
    )
    assert too_much.status_code == 400
    assert too_much.get_json()["code"] == "invalid_entry"

    ok = client.post(
        "/api/nutrition/entries/bulk",
        json={"meal_id": meal_id, "items": [{"product_id": product_id, "amount": 250, "unit": "g"}]},
    )
    assert ok.status_code == 201


def test_product_value_limits(app, client, user):
    login(client)

    response = client.post(
        "/api/nutrition/products",
        json={"name": "Typo", "kcal_per_100g": 2500, "default_unit": "g", "grams_per_unit": 1},
    )
    assert response.status_code == 400
    assert response.get_json()["code"] == "invalid_product"

    response = client.post(
        "/api/nutrition/products",
        json={"name": "Суп", "kcal_per_100g": 45, "fat_per_100g": 0, "default_unit": "g", "grams_per_unit": 1},
    )
    assert response.status_code == 201


def test_water_can_be_corrected_but_not_negative(app, client, user):
    login(client)

    assert client.post("/api/nutrition/water", json={"amount": 0.5}).status_code == 200
    response = client.post("/api/nutrition/water", json={"amount": -0.2})
    assert response.status_code == 200

    response = client.post("/api/nutrition/water", json={"amount": -3})
    assert response.status_code == 200
    with app.app_context():
        from backend.app.models.nutrition.user_water import UserWater

        assert UserWater.query.filter_by(user_id=user.id).first().amount == 0

    bad = client.post("/api/nutrition/water", json={"amount": 12})
    assert bad.status_code == 400
    assert bad.get_json()["code"] == "invalid_water"
    assert client.post("/api/nutrition/water", json={"amount": 0}).status_code == 400


def test_weight_bounds(app, client, user):
    login(client)

    assert client.post("/api/nutrition/weight", json={"weight": 5}).status_code == 400
    assert client.post("/api/nutrition/weight", json={"weight": 900}).status_code == 400
    response = client.post("/api/nutrition/weight", json={"weight": 74.5})
    assert response.status_code == 200
    assert response.get_json()["weight"] == 74.5


def test_copy_meal_keeps_hydration(app, user):
    with app.app_context():
        product = make_product(kcal=0, liquid=100, unit="ml")
        meal = Meal(user_id=user.id, date=date.today() - timedelta(days=1), name="lunch", category="lunch")
        db.session.add(meal)
        db.session.flush()
        db.session.add(
            MealItem(meal_id=meal.id, product_id=product.id, name="Вода", amount=300, unit="ml", weight=300, liquid_ml=300)
        )
        db.session.commit()

        copied = copy_meal_service(user.id, meal.id)
        assert copied.items[0].liquid_ml == 300


def test_translation_falls_back_to_default_locale(app):
    uk = load_translation("uk", "nutrition")
    ru = load_translation("ru", "nutrition")

    def keys(data, prefix=""):
        result = set()
        for key, value in data.items():
            if isinstance(value, dict):
                result |= keys(value, f"{prefix}{key}.")
            else:
                result.add(prefix + key)
        return result

    assert keys(uk) <= keys(ru)
    assert ru["page"]["title"] != uk["page"]["title"]
