"""The category of an own product: form, API, storage and what the quality score does with it."""
import datetime as dt
import json
import re
from pathlib import Path

import pytest

from backend.app.extensions import db
from backend.app.models import Meal, MealItem, Product
from backend.app.services.nutrition import quality_service as q
from backend.app.services.nutrition.item_service import add_item_service
from backend.app.services.nutrition.product_service import PRODUCT_CATEGORIES

ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = ROOT / "web" / "app" / "templates" / "app" / "nutrition" / "modals" / "modal_add_item.html"
LANGUAGES = ("uk", "en", "pl", "ru")

BASE = {"name": "Chicken, homemade", "kcal_per_100g": 120, "protein_per_100g": 24, "fat_per_100g": 2,
        "carbs_per_100g": 0, "salt_per_100g": 0.1, "fiber_per_100g": 0, "sugar_per_100g": 0}


def login(client, user):
    client.post("/auth/login", data={"email": user.email, "password": "password123"})


def create(client, **extra):
    return client.post("/api/nutrition/products", json={**BASE, **extra})


# --- the form ---------------------------------------------------------------

def test_the_form_offers_exactly_the_categories_the_server_accepts():
    source = TEMPLATE.read_text(encoding="utf-8")
    block = source[source.index('id="product-category"'): source.index("</select>", source.index('id="product-category"'))]
    offered = re.findall(r'"([a-z_]+)"', block.split("{% for")[1].split("%}")[0])
    assert set(offered) == PRODUCT_CATEGORIES and len(offered) == len(set(offered))
    assert offered[0] == "other"                       # the default is the first option


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_category_has_a_label_in_every_language(language):
    tree = json.loads((ROOT / "shared" / "translations" / language / "nutrition.json").read_text("utf-8"))["catalog"]
    assert set(tree["categories"]) == PRODUCT_CATEGORIES
    assert all(isinstance(v, str) and v.strip() for v in tree["categories"].values())
    assert tree["productCategory"].strip() and tree["productCategoryHint"].strip()


def test_the_modal_renders_with_labels_in_the_users_language(app, user, client):
    login(client, user)
    html = client.get("/nutrition/").get_data(as_text=True)
    assert 'id="product-category"' in html
    assert html.count('<option value="') >= len(PRODUCT_CATEGORIES)
    for category in PRODUCT_CATEGORIES:
        assert f'<option value="{category}">' in html


def test_the_script_sends_and_restores_the_category():
    source = (ROOT / "web" / "app" / "static" / "ts" / "nutrition" / "modals" / "items.ts").read_text("utf-8")
    compiled = (ROOT / "web" / "app" / "static" / "js" / "nutrition" / "modals" / "items.js").read_text("utf-8")
    for text in (source, compiled):
        assert 'getValue("product-category")' in text          # create and edit both send it
        assert "setProductCategory" in text                     # and the modal restores it
    # Edit and create share one payload: a category is sent on both.
    assert source.count("category: getValue(") == 1 and "updateProduct(editingProduct.id, payload)" in source


# --- create and edit ---------------------------------------------------------

@pytest.mark.parametrize("category", sorted(PRODUCT_CATEGORIES))
def test_every_valid_category_is_stored_and_returned(app, user, client, category):
    login(client, user)
    response = create(client, category=category)
    assert response.status_code == 201
    body = response.get_json()
    assert body["category"] == category
    assert db.session.get(Product, body["id"]).category == category
    mine = client.get("/api/nutrition/products/mine").get_json()["products"]
    assert [p["category"] for p in mine] == [category]


def test_a_missing_or_blank_category_means_other(app, user, client):
    login(client, user)
    assert create(client, name="A").get_json()["category"] == "other"
    assert create(client, name="B", category="").get_json()["category"] == "other"
    assert create(client, name="C", category="  ").get_json()["category"] == "other"
    assert create(client, name="D", category="POULTRY").get_json()["category"] == "poultry"   # case-insensitive


@pytest.mark.parametrize("bad", ["pizza", "meat; drop table", "fruit", "<b>", "other other", 5, ["meat"]])
def test_an_invalid_category_is_refused_and_nothing_is_created(app, user, client, bad):
    login(client, user)
    response = create(client, category=bad)
    assert response.status_code == 400 and response.get_json()["code"] == "invalid_product"
    assert Product.query.filter_by(owner_user_id=user.id).count() == 0


def test_editing_changes_the_category_and_a_bad_one_changes_nothing(app, user, client):
    login(client, user)
    product = create(client).get_json()
    assert product["category"] == "other"

    changed = client.patch(f"/api/nutrition/products/{product['id']}", json={"category": "poultry"})
    assert changed.status_code == 200 and changed.get_json()["category"] == "poultry"
    assert db.session.get(Product, product["id"]).category == "poultry"

    refused = client.patch(f"/api/nutrition/products/{product['id']}", json={"category": "pizza"})
    assert refused.status_code == 400 and refused.get_json()["code"] == "invalid_product"
    db.session.expire_all()
    assert db.session.get(Product, product["id"]).category == "poultry"

    # An edit that does not mention the category keeps it (older clients).
    kept = client.patch(f"/api/nutrition/products/{product['id']}", json={"brand": "Home"})
    assert kept.get_json()["category"] == "poultry"


def test_a_form_sized_edit_payload_round_trips(app, user, client):
    login(client, user)
    product = create(client, category="fish").get_json()
    payload = {"name": "Chicken, homemade", "brand": None, "category": "poultry", "locale": "en",
               "kcal_per_100g": 120, "protein_per_100g": 24, "fat_per_100g": 2, "carbs_per_100g": 0,
               "fiber_per_100g": 0, "sugar_per_100g": None, "liquid_ml_per_100g": 0,
               "default_unit": "g", "grams_per_unit": 1}
    response = client.patch(f"/api/nutrition/products/{product['id']}", json=payload)
    assert response.status_code == 200 and response.get_json()["category"] == "poultry"


def test_old_products_without_a_chosen_category_keep_working(app, user, client):
    login(client, user)
    old = Product(owner_user_id=user.id, source="user", category="other", kcal_per_100g=100, protein_per_100g=1,
                  fat_per_100g=1, carbs_per_100g=1, default_unit="g", grams_per_unit=1, normalized_name="old")
    db.session.add(old)
    db.session.commit()
    mine = client.get("/api/nutrition/products/mine").get_json()["products"]
    assert mine[0]["category"] == "other"
    assert client.patch(f"/api/nutrition/products/{old.id}", json={"brand": "x"}).status_code == 200
    db.session.expire_all()
    assert db.session.get(Product, old.id).category == "other"      # nothing was changed for it


def test_nothing_changes_categories_in_bulk(app, user, client):
    login(client, user)
    ids = [create(client, name=f"P{i}").get_json()["id"] for i in range(3)]
    client.patch(f"/api/nutrition/products/{ids[0]}", json={"category": "fruits"})
    db.session.expire_all()
    assert [db.session.get(Product, i).category for i in ids] == ["fruits", "other", "other"]


# --- what the quality score does with it ------------------------------------------

def log(user, product, grams=300, day=None):
    meal = Meal(user_id=user.id, date=day or dt.date.today(), name="x", category="lunch")
    db.session.add(meal)
    db.session.commit()
    return add_item_service(user.id, {"meal_id": meal.id, "product_id": product.id, "amount": grams, "unit": "g"})


def classify_entry(entry):
    return q.classify_item(q.quality_items([entry])[0])


def test_the_chosen_category_decides_the_class_of_new_entries(app, user, client):
    login(client, user)
    as_other = Product.query.get(create(client, name="Chicken A").get_json()["id"])
    as_poultry = Product.query.get(create(client, name="Chicken B", category="poultry").get_json()["id"])
    as_sweets = Product.query.get(create(client, name="Chicken C", category="sweets").get_json()["id"])
    cured = Product.query.get(create(client, name="Ham D", category="meat", salt_per_100g=3.2).get_json()["id"])
    assert classify_entry(log(user, as_other)) == q.UNKNOWN
    assert classify_entry(log(user, as_poultry)) == q.WHOLE
    assert classify_entry(log(user, as_sweets)) == q.PROCESSED
    assert classify_entry(log(user, cured)) == q.PROCESSED      # the category does not decide alone


def test_a_product_without_salt_in_a_guarded_category_is_unknown_not_whole(app, user, client):
    login(client, user)
    body = {k: v for k, v in BASE.items() if k != "salt_per_100g"}
    product = Product.query.get(client.post("/api/nutrition/products", json={**body, "category": "poultry"}).get_json()["id"])
    assert classify_entry(log(user, product)) == q.UNKNOWN


def test_fixing_the_category_updates_entries_logged_as_other_but_keeps_real_snapshots(app, user, client):
    login(client, user)
    product = Product.query.get(create(client, name="Chicken").get_json()["id"])
    as_other = log(user, product)
    assert as_other.basis["category"] == "other" and classify_entry(as_other) == q.UNKNOWN

    client.patch(f"/api/nutrition/products/{product.id}", json={"category": "poultry"})
    db.session.expire_all()
    as_other = MealItem.query.get(as_other.id)
    assert classify_entry(as_other) == q.WHOLE                       # "other" told nothing: the fix applies
    fixed = log(user, Product.query.get(product.id))
    assert fixed.basis["category"] == "poultry"

    client.patch(f"/api/nutrition/products/{product.id}", json={"category": "sweets"})
    db.session.expire_all()
    # An entry logged as poultry stays poultry; the new sweets category reaches new entries and the "other" one.
    assert classify_entry(MealItem.query.get(fixed.id)) == q.WHOLE
    assert classify_entry(MealItem.query.get(as_other.id)) == q.PROCESSED


def test_the_day_score_gains_the_class_shares_once_the_category_is_set(app, user, client):
    login(client, user)
    products = [Product.query.get(create(client, name=f"Chicken {i}").get_json()["id"]) for i in range(3)]
    for product in products:
        log(user, product, grams=500)                                  # 600 kcal each
    entries = Meal.query.filter_by(user_id=user.id).all()
    items = [i for m in entries for i in m.items]
    before = q.calculate_quality(q.quality_items(items))
    assert before["unclassified_percent"] == 100 and "whole_foods" not in before["components"]

    for product in products:
        client.patch(f"/api/nutrition/products/{product.id}", json={"category": "poultry"})
    db.session.expire_all()
    items = [i for m in Meal.query.filter_by(user_id=user.id).all() for i in m.items]
    after = q.calculate_quality(q.quality_items(items))
    assert after["whole_foods_percent"] == 100 and "whole_foods" in after["components"]


def test_one_category_lookup_for_any_number_of_entries(app, user, client):
    login(client, user)
    products = [Product.query.get(create(client, name=f"P {i}", category="poultry").get_json()["id"]) for i in range(4)]
    items = [log(user, p) for p in products]
    for item in items:
        item.basis = None                                              # legacy entries: category from the product
    db.session.commit()
    from sqlalchemy import event

    loaded = MealItem.query.filter(MealItem.id.in_([i.id for i in items])).all()
    statements = []

    def record(conn, cursor, statement, *args):
        statements.append(statement)

    event.listen(db.engine, "before_cursor_execute", record)
    try:
        result = q.quality_items(loaded)
    finally:
        event.remove(db.engine, "before_cursor_execute", record)
    assert [r["category"] for r in result] == ["poultry"] * 4
    assert len([s for s in statements if "nutrition_products" in s]) == 1
