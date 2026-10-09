"""Products: system vs user, unknown vs zero, duplicates, and search."""

import pytest
from sqlalchemy import event
from werkzeug.security import generate_password_hash

from backend.app.extensions import db
from backend.app.models import Product, ProductName, User
from backend.app.services.nutrition.product_service import (
    ProductServiceError,
    create_user_product,
    search_products_page,
    update_user_product,
)
from backend.app.utils.name_normalization import normalize_name


def system_product(names, kcal=100, carbs=10, sugar=1, fiber=1, key=None, category="other"):
    product = Product(
        source="system", key=key, category=category, kcal_per_100g=kcal,
        protein_per_100g=10, fat_per_100g=5, carbs_per_100g=carbs,
        sugar_per_100g=sugar, fiber_per_100g=fiber, default_unit="g",
        grams_per_unit=1, liquid_ml_per_100g=0,
    )
    product.names = [ProductName(locale=locale, name=name) for locale, name in names.items()]
    db.session.add(product)
    db.session.commit()
    return product


@pytest.fixture
def catalog(app):
    rows = [
        {"uk": "Куряче філе", "en": "Chicken breast", "pl": "Pierś z kurczaka"},
        {"uk": "Куряче філе запечене", "en": "Chicken breast, roasted", "pl": "Pierś z kurczaka pieczona"},
        {"uk": "Куряче філе відварене", "en": "Chicken breast, boiled", "pl": "Pierś z kurczaka gotowana"},
        {"uk": "Яйце куряче", "en": "Egg", "pl": "Jajko"},
        {"uk": "Гречка (суха)", "en": "Buckwheat groats, dry", "pl": "Kasza gryczana"},
        {"uk": "Борошно гречане", "en": "Buckwheat flour", "pl": "Mąka gryczana"},
        {"uk": "Молоко 2,5%", "en": "Milk 2.5%", "pl": "Mleko 2,5%"},
        {"uk": "Яловичина (м'ясо)", "en": "Beef", "pl": "Wołowina"},
        {"uk": "Банан", "en": "Banana", "pl": "Banan"},
    ]
    return {row["en"]: system_product(row, key=f"k{i}") for i, row in enumerate(rows)}


@pytest.fixture
def other_user(app):
    other = User(username="other", email="other@example.com", password=generate_password_hash("password123"))
    db.session.add(other)
    db.session.commit()
    return other


def names(user_id, query, limit=10, offset=0):
    products, _ = search_products_page(user_id, query, "uk", limit, offset=offset)
    return [product["name"] for product in products]


class QueryCounter:
    def __init__(self):
        self.count = 0

    def __call__(self, *args, **kwargs):
        self.count += 1

    def __enter__(self):
        event.listen(db.engine, "before_cursor_execute", self)
        return self

    def __exit__(self, *exc):
        event.remove(db.engine, "before_cursor_execute", self)


# --- normalization ---------------------------------------------------------------


def test_normalize_name_folds_case_apostrophes_punctuation_and_diacritics():
    assert normalize_name("  М'ЯСО  ") == normalize_name("мʼясо") == normalize_name("мясо")
    assert normalize_name("Молоко 2,5%") == normalize_name("молоко 2.5%")
    assert normalize_name("Łosoś") == "losos"
    assert normalize_name("") == ""


# --- search -----------------------------------------------------------------------


def test_prefix_and_ukrainian_search(app, user, catalog):
    found = names(user.id, "куряче")
    assert found[0] == "Куряче філе"  # exact/prefix and shortest first
    assert set(found) >= {"Куряче філе", "Куряче філе запечене", "Куряче філе відварене", "Яйце куряче"}
    assert names(user.id, "ГРЕЧ")[:2] == ["Гречка (суха)", "Борошно гречане"]


def test_typo_tolerant_search(app, user, catalog):
    found = names(user.id, "куряче фле")
    assert found[:3] == ["Куряче філе", "Куряче філе запечене", "Куряче філе відварене"] or (
        found[0] == "Куряче філе" and set(found[:3]) == {
            "Куряче філе", "Куряче філе запечене", "Куряче філе відварене"}
    )
    assert names(user.id, "грчка")[0] == "Гречка (суха)"
    assert names(user.id, "chiken")[0].startswith("Куряче філе")


def test_english_and_polish_names_are_searched_but_shown_in_ukrainian(app, user, catalog):
    assert names(user.id, "chicken breast")[0].startswith("Куряче філе")
    assert names(user.id, "mleko") == ["Молоко 2,5%"]
    assert names(user.id, "milk 2,5") == ["Молоко 2,5%"]


def test_apostrophe_variants_match(app, user, catalog):
    assert names(user.id, "мʼясо") == names(user.id, "м'ясо") == names(user.id, "мясо") == ["Яловичина (м'ясо)"]


def test_no_match_returns_empty(app, user, catalog):
    assert names(user.id, "xyzqwv") == []


def test_server_side_pagination(app, user, catalog):
    first, more = search_products_page(user.id, "куряче", "uk", 2)
    second, more_after = search_products_page(user.id, "куряче", "uk", 2, offset=2)
    assert len(first) == 2 and more is True
    assert {p["id"] for p in first}.isdisjoint({p["id"] for p in second})
    assert more_after is False


def test_user_products_are_searchable_first_and_private(app, user, other_user, catalog):
    create_user_product(user.id, {"name": "Куряче філе домашнє", "kcal_per_100g": 120})
    create_user_product(other_user.id, {"name": "Куряче філе сусіда", "kcal_per_100g": 120})

    found = names(user.id, "куряче філе домашнє")
    assert found == ["Куряче філе домашнє"]
    assert "Куряче філе сусіда" not in names(user.id, "куряче")
    assert "Куряче філе сусіда" in names(other_user.id, "куряче")


def test_search_query_count_is_constant(app, user, catalog):
    # Warm up the connection, then count: no N+1 however many results.
    names(user.id, "куряче")
    with QueryCounter() as exact:
        names(user.id, "куряче")
    with QueryCounter() as fuzzy:
        names(user.id, "куряче фле")
    assert exact.count <= 4
    assert fuzzy.count <= 6


# --- user products: unknown is not zero ----------------------------------------------


def test_user_product_without_sugar_and_fiber_keeps_them_unknown(app, user):
    product = create_user_product(user.id, {
        "name": "Моя домашня гранола", "kcal_per_100g": 450,
        "protein_per_100g": 10, "fat_per_100g": 20, "carbs_per_100g": 55,
    })
    assert product["sugar_per_100g"] is None
    assert product["fiber_per_100g"] is None
    stored = db.session.get(Product, product["id"])
    assert stored.sugar_per_100g is None and stored.fiber_per_100g is None
    assert stored.source == "user" and stored.owner_user_id == user.id


def test_explicit_zero_and_blank_are_different(app, user):
    product = create_user_product(user.id, {
        "name": "Вода з лимоном", "kcal_per_100g": 2, "carbs_per_100g": 0.5,
        "sugar_per_100g": 0, "fiber_per_100g": "",
    })
    assert product["sugar_per_100g"] == 0
    assert product["fiber_per_100g"] is None


def test_sugar_cannot_exceed_carbs(app, user):
    with pytest.raises(ProductServiceError):
        create_user_product(user.id, {"name": "Х", "carbs_per_100g": 10, "sugar_per_100g": 20})


def test_duplicate_user_product_names_are_rejected_per_user(app, user, other_user):
    create_user_product(user.id, {"name": "Мій йогурт", "kcal_per_100g": 80})
    with pytest.raises(ProductServiceError) as error:
        create_user_product(user.id, {"name": "  мій   ЙОГУРТ ", "kcal_per_100g": 90})
    assert error.value.code == "duplicate_product"
    # Another user may use the same name.
    create_user_product(other_user.id, {"name": "Мій йогурт", "kcal_per_100g": 80})


def test_renaming_into_an_existing_name_is_rejected(app, user):
    create_user_product(user.id, {"name": "Хліб домашній"})
    second = create_user_product(user.id, {"name": "Хліб житній"})
    with pytest.raises(ProductServiceError):
        update_user_product(user.id, second["id"], {"name": "хліб домашній"})


def test_clearing_an_optional_value_makes_it_unknown(app, user):
    product = create_user_product(user.id, {"name": "Сирок", "carbs_per_100g": 30, "sugar_per_100g": 20})
    updated = update_user_product(user.id, product["id"], {"sugar_per_100g": None})
    assert updated["sugar_per_100g"] is None


def test_system_products_cannot_be_changed_by_users(app, client, user, catalog):
    client.post("/auth/login", data={"email": "test@example.com", "password": "password123"})
    product = catalog["Banana"]
    response = client.patch(f"/api/nutrition/products/{product.id}", json={"kcal_per_100g": 1})
    assert response.status_code == 404
    db.session.expire_all()
    assert db.session.get(Product, product.id).kcal_per_100g == 100


def test_duplicate_product_api_answers_409(app, client, user):
    client.post("/auth/login", data={"email": "test@example.com", "password": "password123"})
    assert client.post("/api/nutrition/products", json={"name": "Мій хліб"}).status_code == 201
    response = client.post("/api/nutrition/products", json={"name": "мій хліб"})
    assert response.status_code == 409
    assert response.get_json()["code"] == "duplicate_product"
