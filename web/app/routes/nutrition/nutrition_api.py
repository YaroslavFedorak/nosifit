from datetime import date, timedelta

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from backend.app.models import Meal
from backend.app.services.nutrition.calculation_service import NutritionValidationError
from backend.app.services.nutrition.day_service import get_daily_nutrition_data
from backend.app.services.nutrition.meal_categories import normalize_meal_category
from backend.app.services.nutrition.item_service import add_item_service, add_items_service, delete_item_service, update_item_service
from backend.app.services.nutrition.meal_service import add_meal_service, copy_meal_service, delete_meal_service, update_meal_service
from backend.app.services.nutrition.product_service import (
    ProductServiceError,
    archive_user_product,
    create_user_product,
    get_favorites,
    get_product,
    get_recent,
    get_user_products,
    normalize_locale,
    search_products,
    set_favorite,
    update_user_product,
)
from backend.app.services.nutrition.recommendation_service import get_nutrition_recommendations
from backend.app.services.nutrition.serializers import serialize_meal
from backend.app.services.nutrition.stats_service import get_day_details, get_stats, get_year_heatmap
from backend.app.services.nutrition.water_service import add_water_service, get_water_data
from backend.app.services.nutrition.weight_service import get_weight_data, update_user_weight

nutrition_api = Blueprint("nutrition_api", __name__, url_prefix="/api/nutrition")

MIN_WEIGHT_KG = 20.0
MAX_WEIGHT_KG = 400.0
MAX_WATER_LITERS_PER_ENTRY = 5.0
MAX_BULK_ITEMS = 50


def _error(message, code, status=400):
    """JSON error with a stable ``code`` the clients can translate."""
    return jsonify({"error": message, "code": code}), status


def _item_payload(data):
    return {
        "meal_id": data.get("meal_id"),
        "product_id": data.get("product_id"),
        "amount": data.get("amount"),
        "unit": data.get("unit"),
        "locale": data.get("locale", "uk"),
    }


def _entry_update_payload(data):
    payload = {
        "locale": data.get("locale", "uk"),
    }

    for key in ("meal_id", "product_id", "amount", "unit"):
        if key in data:
            payload[key] = data[key]

    return payload


@nutrition_api.get("/day")
@login_required
def api_day():
    return jsonify(get_daily_nutrition_data(
        current_user.id,
        normalize_locale(request.args.get("locale")),
    ))


@nutrition_api.get("/today")
@login_required
def api_today():
    return jsonify(get_daily_nutrition_data(
        current_user.id,
        normalize_locale(request.args.get("locale")),
    ))


@nutrition_api.get("/day/<date_string>")
@login_required
def api_day_details(date_string):
    try:
        target_date = date.fromisoformat(date_string)
    except ValueError:
        return jsonify({"error": "Invalid date"}), 400
    return jsonify(get_day_details(
        current_user.id,
        target_date,
        normalize_locale(request.args.get("locale")),
    ))


@nutrition_api.get("/recommendations")
@login_required
def api_recommendations():
    return jsonify(get_nutrition_recommendations(current_user.id))


@nutrition_api.get("/products")
@login_required
def api_products():
    locale = normalize_locale(request.args.get("locale"))
    query = request.args.get("q", "")
    category = request.args.get("category")

    try:
        limit = int(request.args.get("limit", 20))
    except (TypeError, ValueError):
        limit = 20
    try:
        offset = int(request.args.get("offset", 0))
    except (TypeError, ValueError):
        offset = 0

    return jsonify({
        "products": search_products(
            current_user.id,
            query=query,
            locale=locale,
            limit=limit,
            category=category,
            offset=offset,
        )
    })


@nutrition_api.get("/products/recent")
@login_required
def api_recent_products():
    return jsonify({
        "products": get_recent(
            current_user.id,
            normalize_locale(request.args.get("locale")),
        )
    })


@nutrition_api.get("/products/favorites")
@login_required
def api_favorite_products():
    return jsonify({
        "products": get_favorites(
            current_user.id,
            normalize_locale(request.args.get("locale")),
        )
    })


@nutrition_api.get("/products/mine")
@login_required
def api_my_products():
    return jsonify({
        "products": get_user_products(
            current_user.id,
            normalize_locale(request.args.get("locale")),
        )
    })


@nutrition_api.get("/products/<int:product_id>")
@login_required
def api_product(product_id):
    product = get_product(
        current_user.id,
        product_id,
        normalize_locale(request.args.get("locale")),
    )
    if product is None:
        return jsonify({"error": "Product not found"}), 404
    return jsonify(product)


@nutrition_api.post("/products")
@login_required
def api_create_product():
    data = request.get_json() or {}
    try:
        product = create_user_product(
            current_user.id,
            data,
            normalize_locale(data.get("locale")),
        )
    except ProductServiceError as exc:
        return _error(str(exc), "invalid_product")
    return jsonify(product), 201


@nutrition_api.patch("/products/<int:product_id>")
@login_required
def api_update_product(product_id):
    data = request.get_json() or {}
    try:
        product = update_user_product(
            current_user.id,
            product_id,
            data,
            normalize_locale(data.get("locale")),
        )
    except ProductServiceError as exc:
        return _error(str(exc), "invalid_product")

    if product is None:
        return _error("Product not found", "product_not_found", 404)
    return jsonify(product)


@nutrition_api.delete("/products/<int:product_id>")
@login_required
def api_delete_product(product_id):
    if not archive_user_product(current_user.id, product_id):
        return _error("User product not found", "product_not_found", 404)
    return jsonify({"status": "ok"})


@nutrition_api.post("/products/<int:product_id>/favorite")
@login_required
def api_favorite_product(product_id):
    data = request.get_json() or {}
    product = set_favorite(
        current_user.id,
        product_id,
        bool(data.get("favorite", True)),
        normalize_locale(data.get("locale")),
    )
    if product is None:
        return jsonify({"error": "Product not found"}), 404
    return jsonify(product)


@nutrition_api.post("/meals")
@login_required
def api_add_meal():
    data = request.get_json(silent=True) or {}
    category = (
        normalize_meal_category(data.get("category"))
        or normalize_meal_category(data.get("name"))
    )

    if category is None:
        return _error("Unknown meal category", "invalid_category")

    meal = add_meal_service(
        current_user.id,
        {
            "category": category,
            "time": data.get("time"),
            "date": data.get("date"),
        },
    )
    return jsonify(serialize_meal(meal, normalize_locale(data.get("locale")))), 201


@nutrition_api.put("/meals/<int:meal_id>")
@login_required
def api_edit_meal(meal_id):
    data = request.get_json(silent=True) or {}

    if "category" in data and normalize_meal_category(data.get("category")) is None:
        return _error("Unknown meal category", "invalid_category")

    meal = update_meal_service(
        current_user.id,
        meal_id,
        data,
    )
    if meal is None:
        return _error("Meal not found", "meal_not_found", 404)
    return jsonify(serialize_meal(meal, normalize_locale(data.get("locale")))), 200


@nutrition_api.delete("/meals/<int:meal_id>")
@login_required
def api_delete_meal(meal_id):
    if not delete_meal_service(current_user.id, meal_id):
        return jsonify({"error": "Meal not found"}), 404
    return jsonify({"status": "ok"})


def _legacy_item_to_product(data):
    """
    Temporary compatibility path for the old manual nutrition modal.

    The current nutrition domain is Product -> Entry. Legacy clients used to
    submit a name plus nutrition values directly, so convert that payload into
    a user-owned Product first and let the normal entry service calculate the
    resulting MealItem.
    """
    name = (data.get("name") or "").strip()
    if not name:
        raise NutritionValidationError("Product name is required")

    product = create_user_product(
        current_user.id,
        {
            "name": name,
            "locale": data.get("locale", "uk"),
            "kcal_per_100g": data.get("calories", 0),
            "protein_per_100g": data.get("protein", 0),
            "fat_per_100g": data.get("fat", 0),
            "carbs_per_100g": data.get("carbs", 0),
            "fiber_per_100g": data.get("fiber", 0),
            "default_unit": "g",
            "grams_per_unit": 1,
        },
        normalize_locale(data.get("locale")),
    )

    return product["id"]


def _create_item():
    data = request.get_json() or {}

    if not data.get("meal_id"):
        return jsonify({"error": "meal_id is required"}), 400

    try:
        if not data.get("product_id"):
            data["product_id"] = _legacy_item_to_product(data)
            data["amount"] = 100
            data["unit"] = "g"

        item = add_item_service(current_user.id, _item_payload(data))
    except (NutritionValidationError, ProductServiceError) as exc:
        return _error(str(exc), "invalid_entry")

    if item is None:
        return _error("Meal not found", "meal_not_found", 404)

    return jsonify({
        "id": item.id,
        "status": "ok",
    }), 201


@nutrition_api.post("/entries")
@login_required
def api_add_entry():
    return _create_item()


@nutrition_api.post("/entries/bulk")
@login_required
def api_add_entries_bulk():
    data = request.get_json() or {}
    meal_id = data.get("meal_id")
    items = data.get("items")

    if not meal_id:
        return jsonify({"error": "meal_id is required"}), 400
    if not isinstance(items, list) or not items:
        return jsonify({"error": "items must be a non-empty list"}), 400
    if len(items) > MAX_BULK_ITEMS:
        return _error(f"At most {MAX_BULK_ITEMS} items at once", "invalid_entry")

    payload = []
    for item in items:
        if not isinstance(item, dict):
            return jsonify({"error": "Each item must be an object"}), 400
        payload.append({
            "product_id": item.get("product_id"),
            "amount": item.get("amount"),
            "unit": item.get("unit"),
            "locale": item.get("locale", data.get("locale", "uk")),
        })

    try:
        created = add_items_service(current_user.id, meal_id, payload)
    except (NutritionValidationError, ProductServiceError, TypeError, ValueError) as exc:
        return _error(str(exc), "invalid_entry")

    if created is None:
        return _error("Meal not found", "meal_not_found", 404)

    return jsonify({
        "status": "ok",
        "ids": [item.id for item in created],
    }), 201


@nutrition_api.post("/items")
@login_required
def api_add_item():
    return _create_item()


def _update_item(item_id):
    data = request.get_json() or {}

    try:
        if not data.get("product_id") and "name" in data:
            data["product_id"] = _legacy_item_to_product(data)
            data["amount"] = 100
            data["unit"] = "g"

        item = update_item_service(
            current_user.id,
            item_id,
            _entry_update_payload(data),
        )
    except (NutritionValidationError, ProductServiceError) as exc:
        return _error(str(exc), "invalid_entry")

    if item is None:
        return _error("Entry not found", "entry_not_found", 404)

    return jsonify({
        "id": item.id,
        "status": "ok",
    })


@nutrition_api.patch("/entries/<int:item_id>")
@login_required
def api_update_entry(item_id):
    return _update_item(item_id)


@nutrition_api.put("/items/<int:item_id>")
@login_required
def api_edit_item(item_id):
    return _update_item(item_id)


def _delete_item(item_id):
    if not delete_item_service(current_user.id, item_id):
        return jsonify({"error": "Entry not found"}), 404
    return jsonify({"status": "ok"})


@nutrition_api.delete("/entries/<int:item_id>")
@login_required
def api_delete_entry(item_id):
    return _delete_item(item_id)


@nutrition_api.delete("/items/<int:item_id>")
@login_required
def api_delete_item(item_id):
    return _delete_item(item_id)


@nutrition_api.post("/copy-yesterday")
@login_required
def api_copy_yesterday():
    yesterday = date.today() - timedelta(days=1)
    meals = Meal.query.filter_by(
        user_id=current_user.id,
        date=yesterday,
    ).all()

    if not meals:
        return _error("No meals found yesterday", "nothing_to_copy")

    copied = []
    for meal in meals:
        new_meal = copy_meal_service(current_user.id, meal.id)
        if new_meal:
            copied.append(new_meal.id)

    return jsonify({"status": "ok", "copied": len(copied)})


@nutrition_api.post("/weight")
@login_required
def api_update_weight():
    data = request.get_json() or {}
    try:
        weight = float(data.get("weight"))
    except (TypeError, ValueError):
        return _error("Invalid weight", "invalid_weight")

    if not (MIN_WEIGHT_KG <= weight <= MAX_WEIGHT_KG):
        return _error(
            f"Weight must be between {MIN_WEIGHT_KG:g} and {MAX_WEIGHT_KG:g} kg",
            "invalid_weight",
        )

    entry = update_user_weight(current_user, weight)
    return jsonify({"status": "ok", "weight": entry.weight})


@nutrition_api.get("/weight")
@login_required
def api_get_weight():
    return jsonify(get_weight_data(current_user.id))


@nutrition_api.get("/stats")
@login_required
def api_stats():
    try:
        days = int(request.args.get("days", 7))
    except (TypeError, ValueError):
        days = 7

    days = max(1, min(days, 365))
    return jsonify(get_stats(current_user.id, days))


@nutrition_api.get("/heatmap")
@login_required
def api_heatmap():
    try:
        year = int(request.args.get("year", date.today().year))
    except (TypeError, ValueError):
        year = date.today().year
    if not 2000 <= year <= 2100:
        return _error("Year is out of range", "invalid_year")
    return jsonify(get_year_heatmap(current_user.id, year))


@nutrition_api.get("/water")
@login_required
def api_get_water():
    return jsonify(get_water_data(current_user.id))


@nutrition_api.post("/water")
@login_required
def api_add_water():
    data = request.get_json() or {}
    try:
        amount = float(data.get("amount"))
    except (TypeError, ValueError):
        return _error("Invalid amount", "invalid_water")

    # Negative values subtract (fixing a mistaken entry).
    if amount == 0 or abs(amount) > MAX_WATER_LITERS_PER_ENTRY:
        return _error(
            f"Amount must be between -{MAX_WATER_LITERS_PER_ENTRY:g} and {MAX_WATER_LITERS_PER_ENTRY:g} L",
            "invalid_water",
        )

    add_water_service(current_user.id, amount)
    water_data = get_water_data(current_user.id)

    return jsonify({
        "status": "ok",
        "amount": water_data["amount"],
        "recommended": water_data["recommended"],
    })
