from sqlalchemy import text

from backend.app.extensions import db
from backend.app.models import Meal, MealItem, Product, ProductName, User
from backend.app.services.nutrition.item_service import (
    add_item_service,
    add_items_service,
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
from backend.app.services.nutrition.water_service import add_water_service
from migrations.versions.d1a6c4e9b7f2_fix_historical_liquid_values import (
    HISTORICAL_LIQUID_FIX_SQL,
)


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
        liquid_ml_per_100g=0,
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


def test_beverage_entry_contributes_to_combined_water_total(app, user):
    with app.app_context():
        product = Product(
            source="system",
            kcal_per_100g=2,
            protein_per_100g=0.3,
            fat_per_100g=0,
            carbs_per_100g=0,
            fiber_per_100g=0,
            liquid_ml_per_100g=100,
            default_unit="ml",
            grams_per_unit=1,
        )
        db.session.add(product)
        db.session.flush()

        db.session.add(
            ProductName(
                product_id=product.id,
                locale="uk",
                name="Кава чорна",
            )
        )

        meal = make_meal(user.id)

        entry = add_item_service(
            user.id,
            {
                "meal_id": meal.id,
                "product_id": product.id,
                "amount": 300,
                "unit": "ml",
                "locale": "uk",
            },
        )

        add_water_service(user.id, 0.5)

        day_data = get_day_details(
            user.id,
            meal.date,
            "uk",
        )

        assert entry.liquid_ml == 300
        assert day_data["water"] == 0.8



def make_beverage_product(liquid_ml_per_100g=100, grams_per_unit=1):
    product = Product(
        source="system",
        kcal_per_100g=2,
        protein_per_100g=0.3,
        fat_per_100g=0,
        carbs_per_100g=0,
        fiber_per_100g=0,
        liquid_ml_per_100g=liquid_ml_per_100g,
        default_unit="ml",
        grams_per_unit=grams_per_unit,
    )
    db.session.add(product)
    db.session.flush()
    db.session.add(
        ProductName(
            product_id=product.id,
            locale="uk",
            name="Напій",
        )
    )
    db.session.commit()
    return product


def test_bulk_and_regular_beverage_addition_store_same_liquid(app, user):
    with app.app_context():
        product = make_beverage_product()
        regular_meal = make_meal(user.id, "Звичайне")
        bulk_meal = make_meal(user.id, "Bulk")

        regular = add_item_service(
            user.id,
            {
                "meal_id": regular_meal.id,
                "product_id": product.id,
                "amount": 300,
                "unit": "ml",
            },
        )
        bulk = add_items_service(
            user.id,
            bulk_meal.id,
            [{
                "product_id": product.id,
                "amount": 300,
                "unit": "ml",
            }],
        )[0]

        assert regular.liquid_ml == 300
        assert bulk.liquid_ml == 300


def test_edit_and_delete_beverage_update_daily_fluid(app, user):
    with app.app_context():
        product = make_beverage_product()
        meal = make_meal(user.id)

        entry = add_item_service(
            user.id,
            {
                "meal_id": meal.id,
                "product_id": product.id,
                "amount": 300,
                "unit": "ml",
            },
        )

        assert get_day_details(user.id, meal.date, "uk")["water"] == 0.3

        update_item_service(
            user.id,
            entry.id,
            {
                "amount": 500,
                "unit": "ml",
            },
        )
        assert get_day_details(user.id, meal.date, "uk")["water"] == 0.5

        assert delete_item_service(user.id, entry.id) is True
        assert get_day_details(user.id, meal.date, "uk")["water"] == 0.0


def test_manual_water_is_not_duplicated_with_beverage(app, user):
    with app.app_context():
        product = make_beverage_product()
        meal = make_meal(user.id)

        add_item_service(
            user.id,
            {
                "meal_id": meal.id,
                "product_id": product.id,
                "amount": 300,
                "unit": "ml",
            },
        )
        add_water_service(user.id, 0.5)

        assert get_day_details(user.id, meal.date, "uk")["water"] == 0.8


def test_liquid_volume_does_not_use_grams_per_unit_for_ml_input(app, user):
    with app.app_context():
        product = make_beverage_product(
            liquid_ml_per_100g=80,
            grams_per_unit=0.75,
        )
        meal = make_meal(user.id)

        entry = add_item_service(
            user.id,
            {
                "meal_id": meal.id,
                "product_id": product.id,
                "amount": 200,
                "unit": "ml",
            },
        )

        assert entry.liquid_ml == 200


def test_migration_backfill_uses_stored_weight_in_grams(app, user):
    with app.app_context():
        product = make_beverage_product(
            liquid_ml_per_100g=80,
            grams_per_unit=250,
        )
        meal = make_meal(user.id)

        old_item = MealItem(
            meal_id=meal.id,
            product_id=product.id,
            name="Старий напій",
            amount=1.2,
            unit="pcs",
            weight=300,
            liquid_ml=0,
            calories=0,
            protein=0,
            fat=0,
            carbs=0,
            fiber=0,
        )
        db.session.add(old_item)
        db.session.commit()

        db.session.execute(text(HISTORICAL_LIQUID_FIX_SQL))
        db.session.commit()
        db.session.refresh(old_item)

        assert old_item.liquid_ml == 240
