from backend.app.extensions import db
from backend.app.models import Meal, Product, ProductName, User
from backend.app.services.nutrition.item_service import (
    add_item_service,
    delete_item_service,
    update_item_service,
)
from backend.app.services.nutrition.product_service import (
    create_user_product,
    get_product,
    set_favorite,
)
from backend.app.services.nutrition.serializers import serialize_meal
from backend.app.services.nutrition.stats_service import get_day_details


def make_system_product():
    product = Product(
        source="system",
        kcal_per_100g=165,
        protein_per_100g=31,
        fat_per_100g=3.6,
        carbs_per_100g=0,
        fiber_per_100g=0,
        default_unit="g",
        grams_per_unit=1,
    )
    db.session.add(product)
    db.session.flush()

    db.session.add_all([
        ProductName(
            product_id=product.id,
            locale="uk",
            name="Куряче філе",
        ),
        ProductName(
            product_id=product.id,
            locale="en",
            name="Chicken breast",
        ),
    ])
    db.session.commit()
    return product


def make_meal(user_id, name="Обід"):
    meal = Meal(
        user_id=user_id,
        date=__import__("datetime").date.today(),
        name=name,
        category="Обід",
    )
    db.session.add(meal)
    db.session.commit()
    return meal


def test_product_amount_calculation_and_meal_totals(app, user):
    with app.app_context():
        product = make_system_product()
        meal = make_meal(user.id)

        entry = add_item_service(
            user.id,
            {
                "meal_id": meal.id,
                "product_id": product.id,
                "amount": 200,
                "unit": "g",
                "locale": "uk",
            },
        )

        assert entry.calories == 330
        assert entry.protein == 62
        assert entry.fat == 7.2
        assert meal.total_calories == 330
        assert meal.total_protein == 62
        assert meal.total_fat == 7.2


def test_edit_amount_recalculates_totals(app, user):
    with app.app_context():
        product = make_system_product()
        meal = make_meal(user.id)

        entry = add_item_service(
            user.id,
            {
                "meal_id": meal.id,
                "product_id": product.id,
                "amount": 200,
                "unit": "g",
            },
        )

        update_item_service(
            user.id,
            entry.id,
            {
                "amount": 250,
                "unit": "g",
            },
        )

        assert entry.calories == 412
        assert entry.protein == 77.5
        assert meal.total_calories == 412


def test_move_and_delete_entry_recalculate_meals(app, user):
    with app.app_context():
        product = make_system_product()
        lunch = make_meal(user.id, "Обід")
        dinner = make_meal(user.id, "Вечеря")

        entry = add_item_service(
            user.id,
            {
                "meal_id": lunch.id,
                "product_id": product.id,
                "amount": 200,
                "unit": "g",
            },
        )

        update_item_service(
            user.id,
            entry.id,
            {
                "meal_id": dinner.id,
                "amount": 200,
                "unit": "g",
            },
        )

        assert lunch.total_calories == 0
        assert dinner.total_calories == 330

        assert delete_item_service(user.id, entry.id) is True
        assert dinner.total_calories == 0


def test_user_product_isolated_from_other_user(app, user):
    with app.app_context():
        other = User(
            username="other",
            email="other@example.com",
            password="hash",
        )
        db.session.add(other)
        db.session.commit()

        product = create_user_product(
            user.id,
            {
                "name": "My yogurt",
                "kcal_per_100g": 100,
                "protein_per_100g": 10,
                "fat_per_100g": 2,
                "carbs_per_100g": 5,
                "fiber_per_100g": 0,
                "default_unit": "g",
                "grams_per_unit": 1,
                "locale": "en",
            },
            "en",
        )

        assert get_product(user.id, product["id"], "en") is not None
        assert get_product(other.id, product["id"], "en") is None


def test_favorite_and_serialization(app, user):
    with app.app_context():
        product = make_system_product()
        meal = make_meal(user.id)

        add_item_service(
            user.id,
            {
                "meal_id": meal.id,
                "product_id": product.id,
                "amount": 100,
                "unit": "g",
            },
        )

        favorite = set_favorite(
            user.id,
            product.id,
            True,
            "uk",
        )

        assert favorite["is_favorite"] is True

        serialized = serialize_meal(meal, "uk")
        assert serialized["items"][0]["product_id"] == product.id
        assert serialized["items"][0]["amount"] == 100

    
def test_product_names_are_localized_in_meal_and_day_serializers(app, user):
    with app.app_context():
        product = make_system_product()
        meal = make_meal(user.id)

        add_item_service(
            user.id,
            {
                "meal_id": meal.id,
                "product_id": product.id,
                "amount": 100,
                "unit": "g",
                "locale": "uk",
            },
        )

        meal_data = serialize_meal(meal, "en")
        day_data = get_day_details(
            user.id,
            meal.date,
            "en",
        )

        assert meal_data["items"][0]["name"] == "Chicken breast"
        assert day_data["meals"][0]["items"][0]["name"] == "Chicken breast"
