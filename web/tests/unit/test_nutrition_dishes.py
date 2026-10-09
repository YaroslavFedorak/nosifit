"""Reusable dishes, logging with snapshots, and known-vs-unknown totals."""

from datetime import date

import pytest
from werkzeug.security import generate_password_hash

from backend.app.extensions import db
from backend.app.models import Dish, DishItem, Meal, MealItem, Product, ProductName, User
from backend.app.services.account_service import delete_user_account
from backend.app.services.nutrition.calculation_service import calculate_product_nutrition
from web.tests.unit.test_nutrition_search import QueryCounter


def login(client, email="test@example.com"):
    return client.post("/auth/login", data={"email": email, "password": "password123"})


def product(name, kcal, protein=0.0, fat=0.0, carbs=0.0, sugar=0.0, fiber=0.0,
            unit="g", grams_per_unit=1.0, owner=None):
    row = Product(
        source="user" if owner else "system", owner_user_id=owner, category="other",
        kcal_per_100g=kcal, protein_per_100g=protein, fat_per_100g=fat,
        carbs_per_100g=carbs, sugar_per_100g=sugar, fiber_per_100g=fiber,
        default_unit=unit, grams_per_unit=grams_per_unit, liquid_ml_per_100g=0,
    )
    row.names = [ProductName(locale="uk", name=name)]
    db.session.add(row)
    db.session.commit()
    return row


@pytest.fixture
def food(app):
    return {
        "oats": product("Вівсянка", 370, protein=11, fat=7.7, carbs=58, sugar=1.8, fiber=10.6),
        "milk": product("Молоко 2,5%", 55, protein=3.4, fat=2.5, carbs=4.8, sugar=4.5, fiber=0,
                        unit="ml", grams_per_unit=1.03),
        "banana": product("Банан", 90, protein=1, fat=0.3, carbs=20, sugar=15.6, fiber=2.7),
        "peanut": product("Арахісова паста", 636, protein=22, fat=52, carbs=16, sugar=10.5, fiber=5),
        "apple": product("Яблуко", 52, protein=0.3, fat=0.2, carbs=12, sugar=9.4, fiber=1.4),
    }


def oatmeal_payload(food, name="Моя вівсянка"):
    return {
        "name": name,
        "items": [
            {"product_id": food["oats"].id, "amount": 80, "unit": "g"},
            {"product_id": food["milk"].id, "amount": 250, "unit": "ml"},
            {"product_id": food["banana"].id, "amount": 120, "unit": "g"},
            {"product_id": food["peanut"].id, "amount": 20, "unit": "g"},
        ],
    }


@pytest.fixture
def oatmeal(client, user, food):
    login(client)
    response = client.post("/api/nutrition/dishes", json=oatmeal_payload(food))
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def today_entries(user_id):
    db.session.expire_all()
    return (
        MealItem.query.join(Meal)
        .filter(Meal.user_id == user_id, Meal.date == date.today())
        .order_by(MealItem.id)
        .all()
    )


# --- dish CRUD -----------------------------------------------------------------------


def test_create_dish_returns_components_and_totals(oatmeal, food):
    assert oatmeal["name"] == "Моя вівсянка"
    assert [item["amount"] for item in oatmeal["items"]] == [80, 250, 120, 20]
    milk = oatmeal["items"][1]
    assert milk["unit"] == "ml" and milk["grams"] == pytest.approx(257.5)
    expected = sum(item["calories"] for item in oatmeal["items"])
    assert oatmeal["totals"]["calories"] == pytest.approx(expected, abs=1)
    assert oatmeal["totals"]["fiber_complete"] is True


def test_list_get_edit_delete_dish(client, oatmeal, food):
    listed = client.get("/api/nutrition/dishes").get_json()
    assert [dish["id"] for dish in listed["dishes"]] == [oatmeal["id"]]
    assert listed["has_more"] is False

    assert client.get(f"/api/nutrition/dishes/{oatmeal['id']}").get_json()["name"] == "Моя вівсянка"

    # Change an amount, remove a product, replace one, add one: PATCH sends
    # the whole new composition.
    response = client.patch(f"/api/nutrition/dishes/{oatmeal['id']}", json={
        "name": "Вівсянка вихідного дня",
        "items": [
            {"product_id": food["oats"].id, "amount": 100, "unit": "g"},
            {"product_id": food["milk"].id, "amount": 200, "unit": "ml"},
            {"product_id": food["apple"].id, "amount": 150, "unit": "g"},
        ],
    })
    assert response.status_code == 200, response.get_json()
    edited = response.get_json()
    assert edited["name"] == "Вівсянка вихідного дня"
    assert [(i["name"], i["amount"]) for i in edited["items"]] == [
        ("Вівсянка", 100), ("Молоко 2,5%", 200), ("Яблуко", 150),
    ]
    assert DishItem.query.count() == 3

    assert client.delete(f"/api/nutrition/dishes/{oatmeal['id']}").status_code == 200
    assert Dish.query.count() == 0 and DishItem.query.count() == 0
    assert client.get(f"/api/nutrition/dishes/{oatmeal['id']}").status_code == 404


def test_search_dishes_by_name(client, oatmeal, food):
    client.post("/api/nutrition/dishes", json={
        "name": "Салат", "items": [{"product_id": food["apple"].id, "amount": 100}],
    })
    found = client.get("/api/nutrition/dishes?q=вівс").get_json()["dishes"]
    assert [dish["name"] for dish in found] == ["Моя вівсянка"]


def test_same_product_twice_is_merged_not_duplicated(client, user, food):
    login(client)
    dish = client.post("/api/nutrition/dishes", json={
        "name": "Банани",
        "items": [
            {"product_id": food["banana"].id, "amount": 100, "unit": "g"},
            {"product_id": food["banana"].id, "amount": 50, "unit": "g"},
        ],
    }).get_json()
    assert [(i["name"], i["amount"]) for i in dish["items"]] == [("Банан", 150)]


def test_dish_validation_errors(client, user, food):
    login(client)
    assert client.post("/api/nutrition/dishes", json={"name": "", "items": []}).status_code == 400
    assert client.post("/api/nutrition/dishes", json={"name": "Х", "items": []}).status_code == 400
    response = client.post("/api/nutrition/dishes", json={
        "name": "Х", "items": [{"product_id": 999999, "amount": 10}],
    })
    assert response.status_code == 404
    response = client.post("/api/nutrition/dishes", json={
        "name": "Х", "items": [{"product_id": food["oats"].id, "amount": -5}],
    })
    assert response.status_code == 400


def test_duplicate_dish_name_is_rejected(client, oatmeal, food):
    response = client.post("/api/nutrition/dishes", json=oatmeal_payload(food, "моя  ВІВСЯНКА"))
    assert response.status_code == 409
    assert response.get_json()["code"] == "duplicate_dish"


def test_dishes_and_their_products_are_private(app, client, user, food, oatmeal):
    other = User(username="bob", email="bob@example.com", password=generate_password_hash("password123"))
    db.session.add(other)
    db.session.commit()
    secret = product("Секретний соус", 300, owner=user.id)

    client.post("/auth/logout")
    login(client, "bob@example.com")
    assert client.get(f"/api/nutrition/dishes/{oatmeal['id']}").status_code == 404
    assert client.patch(f"/api/nutrition/dishes/{oatmeal['id']}", json={"name": "x"}).status_code == 404
    assert client.delete(f"/api/nutrition/dishes/{oatmeal['id']}").status_code == 404
    assert client.post("/api/nutrition/log", json={
        "category": "breakfast", "dish_id": oatmeal["id"],
    }).status_code == 404
    # Someone else's product cannot go into your dish or meal.
    response = client.post("/api/nutrition/dishes", json={
        "name": "Чужий", "items": [{"product_id": secret.id, "amount": 10}],
    })
    assert response.status_code == 404
    response = client.post("/api/nutrition/log", json={
        "category": "lunch", "items": [{"product_id": secret.id, "amount": 10}],
    })
    assert response.status_code == 404
    assert Dish.query.filter_by(user_id=other.id).count() == 0


# --- logging a dish -------------------------------------------------------------------


def test_log_dish_as_saved_in_one_request(client, user, oatmeal, food):
    response = client.post("/api/nutrition/log", json={
        "category": "breakfast", "dish_id": oatmeal["id"], "time": "08:15",
    })
    assert response.status_code == 201, response.get_json()
    body = response.get_json()
    assert body["meal"]["category"] == "breakfast" and body["meal"]["time"] == "08:15"

    entries = today_entries(user.id)
    assert [(e.name, e.amount, e.dish_id, e.dish_name) for e in entries] == [
        ("Вівсянка", 80, oatmeal["id"], "Моя вівсянка"),
        ("Молоко 2,5%", 250, oatmeal["id"], "Моя вівсянка"),
        ("Банан", 120, oatmeal["id"], "Моя вівсянка"),
        ("Арахісова паста", 20, oatmeal["id"], "Моя вівсянка"),
    ]
    assert sum(e.calories for e in entries) == pytest.approx(oatmeal["totals"]["calories"], abs=2)
    dish = db.session.get(Dish, oatmeal["id"])
    assert dish.use_count == 1 and dish.last_used_at is not None


def test_log_returns_the_day_for_clients_that_render_it(client, oatmeal):
    body = client.post("/api/nutrition/log", json={
        "category": "breakfast", "dish_id": oatmeal["id"], "return": "day",
    }).get_json()
    assert body["day"]["progress"]["calories"] == pytest.approx(oatmeal["totals"]["calories"], abs=2)
    assert len(body["day"]["meals"]) == 1


def test_log_reuses_the_meal_of_the_same_category(client, user, oatmeal, food):
    client.post("/api/nutrition/log", json={"category": "breakfast", "dish_id": oatmeal["id"]})
    client.post("/api/nutrition/log", json={
        "category": "breakfast", "items": [{"product_id": food["apple"].id, "amount": 100}],
    })
    assert Meal.query.filter_by(user_id=user.id).count() == 1
    assert len(today_entries(user.id)) == 5


def test_editing_before_logging_changes_only_this_meal(client, user, oatmeal, food):
    # This time: more oats, less milk, banana replaced by an apple, no peanut butter.
    response = client.post("/api/nutrition/log", json={
        "category": "breakfast",
        "dish_id": oatmeal["id"],
        "items": [
            {"product_id": food["oats"].id, "amount": 100, "unit": "g"},
            {"product_id": food["milk"].id, "amount": 200, "unit": "ml"},
            {"product_id": food["apple"].id, "amount": 150, "unit": "g"},
        ],
    })
    assert response.status_code == 201
    assert [(e.name, e.amount) for e in today_entries(user.id)] == [
        ("Вівсянка", 100), ("Молоко 2,5%", 200), ("Яблуко", 150),
    ]
    # The template is untouched.
    template = client.get(f"/api/nutrition/dishes/{oatmeal['id']}").get_json()
    assert [(i["name"], i["amount"]) for i in template["items"]] == [
        ("Вівсянка", 80), ("Молоко 2,5%", 250), ("Банан", 120), ("Арахісова паста", 20),
    ]


def test_changing_the_template_never_changes_logged_meals(client, user, oatmeal, food):
    client.post("/api/nutrition/log", json={"category": "breakfast", "dish_id": oatmeal["id"]})
    before = [(e.name, e.amount, e.calories) for e in today_entries(user.id)]

    client.patch(f"/api/nutrition/dishes/{oatmeal['id']}", json={
        "items": [{"product_id": food["apple"].id, "amount": 500}],
    })
    assert [(e.name, e.amount, e.calories) for e in today_entries(user.id)] == before

    # Deleting the dish keeps the entries; only the link goes.
    client.delete(f"/api/nutrition/dishes/{oatmeal['id']}")
    entries = today_entries(user.id)
    assert [(e.name, e.amount, e.calories) for e in entries] == before
    assert {e.dish_id for e in entries} == {None}
    assert {e.dish_name for e in entries} == {"Моя вівсянка"}


def test_changing_a_product_never_changes_logged_meals(client, user):
    login(client)
    yogurt = client.post("/api/nutrition/products", json={
        "name": "Мій йогурт", "kcal_per_100g": 60, "protein_per_100g": 5, "carbs_per_100g": 4,
        "sugar_per_100g": 4,
    }).get_json()
    client.post("/api/nutrition/log", json={
        "category": "snack", "items": [{"product_id": yogurt["id"], "amount": 200}],
    })
    client.patch(f"/api/nutrition/products/{yogurt['id']}", json={
        "name": "Мій йогурт 5%", "kcal_per_100g": 120, "sugar_per_100g": None,
    })

    entry = today_entries(user.id)[0]
    assert (entry.calories, entry.sugar, entry.name) == (120, 8, "Мій йогурт")
    day = client.get("/api/nutrition/day").get_json()
    assert day["meals"][0]["items"][0]["name"] == "Мій йогурт"

    # Editing the amount rescales from the entry's own snapshot.
    client.patch(f"/api/nutrition/entries/{entry.id}", json={"amount": 100})
    entry = today_entries(user.id)[0]
    assert (entry.calories, entry.sugar) == (60, 4)


def test_archived_own_product_still_works_inside_a_saved_dish(client, user, food):
    login(client)
    mine = client.post("/api/nutrition/products", json={"name": "Мій хліб", "kcal_per_100g": 250}).get_json()
    dish = client.post("/api/nutrition/dishes", json={
        "name": "Тост", "items": [{"product_id": mine["id"], "amount": 50}],
    }).get_json()
    client.delete(f"/api/nutrition/products/{mine['id']}")

    preview = client.get(f"/api/nutrition/dishes/{dish['id']}").get_json()
    assert preview["items"][0]["is_active"] is False
    assert client.post("/api/nutrition/log", json={
        "category": "breakfast", "dish_id": dish["id"],
    }).status_code == 201


def test_log_validation(client, user, oatmeal, food):
    assert client.post("/api/nutrition/log", json={"dish_id": oatmeal["id"]}).status_code == 400
    assert client.post("/api/nutrition/log", json={"category": "lunch"}).status_code == 400
    assert client.post("/api/nutrition/log", json={
        "category": "lunch", "items": [{"product_id": food["apple"].id, "amount": 99999}],
    }).status_code == 400
    assert Meal.query.count() == 0  # nothing half-written


# --- calculation: known vs unknown -----------------------------------------------------


def test_product_calculation_keeps_unknown_values_unknown(app):
    known = product("Відоме", 100, carbs=10, sugar=5, fiber=2)
    unknown = product("Невідоме", 100, carbs=10, sugar=None, fiber=None)
    assert calculate_product_nutrition(known, 200, "g").fiber == 4
    result = calculate_product_nutrition(unknown, 200, "g")
    assert result.fiber is None and result.sugar is None
    assert result.calories == 200


def test_meal_and_day_totals_separate_known_and_unknown(client, user, food):
    login(client)
    mystery = client.post("/api/nutrition/products", json={
        "name": "Гранола", "kcal_per_100g": 450, "carbs_per_100g": 60,
    }).get_json()

    client.post("/api/nutrition/log", json={
        "category": "breakfast", "items": [{"product_id": mystery["id"], "amount": 50}],
    })
    day = client.get("/api/nutrition/day").get_json()
    assert day["fiber"] is None and day["progress"]["fiber"] is None  # "—", not 0 g
    assert day["meals"][0]["total_fiber"] is None

    client.post("/api/nutrition/log", json={
        "category": "breakfast", "items": [{"product_id": food["oats"].id, "amount": 50}],
    })
    day = client.get("/api/nutrition/day").get_json()
    assert day["fiber"] == pytest.approx(5.3)
    assert day["fiber_complete"] is False  # a lower bound
    assert day["sugar"] == pytest.approx(0.9)

    details = client.get(f"/api/nutrition/day/{date.today().isoformat()}").get_json()
    assert details["fiber"] == pytest.approx(5.3) and details["fiber_complete"] is False


def test_empty_day_has_known_zero(client, user):
    login(client)
    day = client.get("/api/nutrition/day").get_json()
    assert day["fiber"] == 0 and day["fiber_complete"] is True


def test_dish_totals_mark_partly_unknown_fiber(client, user, food):
    login(client)
    mystery = client.post("/api/nutrition/products", json={"name": "Сироп", "kcal_per_100g": 300}).get_json()
    dish = client.post("/api/nutrition/dishes", json={
        "name": "Каша з сиропом",
        "items": [
            {"product_id": food["oats"].id, "amount": 100},
            {"product_id": mystery["id"], "amount": 20},
        ],
    }).get_json()
    assert dish["totals"]["fiber"] == pytest.approx(10.6)
    assert dish["totals"]["fiber_complete"] is False


# --- efficiency and lifecycle ----------------------------------------------------------


def test_logging_and_listing_use_a_constant_number_of_queries(client, user, food):
    login(client)
    for index in range(5):
        client.post("/api/nutrition/dishes", json={**oatmeal_payload(food), "name": f"Страва {index}"})
    dish_id = Dish.query.first().id

    client.get("/api/nutrition/dishes")  # warm up
    with QueryCounter() as listing:
        response = client.get("/api/nutrition/dishes")
    assert len(response.get_json()["dishes"]) == 5
    with QueryCounter() as logging:
        assert client.post("/api/nutrition/log", json={
            "category": "lunch", "dish_id": dish_id,
        }).status_code == 201
    # Independent of the number of dishes or components (no N+1); the
    # remaining queries are the login/session bookkeeping of the request.
    assert listing.count <= 8, listing.count
    assert logging.count <= 16, logging.count


def test_deleting_the_account_removes_dishes(app, client, user, oatmeal):
    client.post("/api/nutrition/log", json={"category": "breakfast", "dish_id": oatmeal["id"]})
    delete_user_account(db.session.get(User, user.id))
    assert Dish.query.count() == 0 and DishItem.query.count() == 0 and MealItem.query.count() == 0
