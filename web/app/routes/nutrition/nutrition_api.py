from datetime import date, timedelta

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from web.app.models import Meal

from web.app.services.nutrition.day_service import (
    get_daily_nutrition_data,
)

from web.app.services.nutrition.item_service import (
    add_item_service,
    delete_item_service,
    update_item_service,
)

from web.app.services.nutrition.meal_service import (
    add_meal_service,
    copy_meal_service,
    delete_meal_service,
    update_meal_service,
)

from web.app.services.nutrition.recommendation_service import (
    get_nutrition_recommendations,
)

from web.app.services.nutrition.stats_service import (
    get_stats,
    get_year_heatmap,
)

from web.app.services.nutrition.water_service import (
    add_water_service,
    get_water_data,
)

from web.app.services.nutrition.weight_service import (
    get_weight_data,
    update_user_weight,
)

nutrition_api = Blueprint(
    "nutrition_api",
    __name__,
    url_prefix="/api/nutrition",
)


@nutrition_api.get("/day")
@login_required
def api_day():
    data = get_daily_nutrition_data(
        current_user.id,
    )

    return jsonify(data)


@nutrition_api.get("/recommendations")
@login_required
def api_recommendations():
    data = get_nutrition_recommendations(
        current_user.id,
    )

    return jsonify(data)


@nutrition_api.post("/meals")
@login_required
def api_add_meal():
    data = request.get_json() or {}

    name = (data.get("name") or "").strip()
    category = (data.get("category") or "").strip()

    if not name or not category:
        return (
            jsonify(
                {
                    "error": "Name and category are required",
                }
            ),
            400,
        )

    meal = add_meal_service(
        current_user.id,
        {
            "name": name,
            "category": category,
            "time": data.get("time"),
        },
    )

    return (
        jsonify(
            {
                "status": "ok",
                "meal_id": meal.id,
            }
        ),
        201,
    )


@nutrition_api.put("/meals/<int:meal_id>")
@login_required
def api_edit_meal(meal_id):
    data = request.get_json() or {}

    meal = update_meal_service(
        current_user.id,
        meal_id,
        data,
    )

    if meal is None:
        return (
            jsonify(
                {
                    "error": "Meal not found",
                }
            ),
            404,
        )

    return jsonify(
        {
            "status": "ok",
        }
    )


@nutrition_api.delete("/meals/<int:meal_id>")
@login_required
def api_delete_meal(meal_id):
    deleted = delete_meal_service(
        current_user.id,
        meal_id,
    )

    if not deleted:
        return (
            jsonify(
                {
                    "error": "Meal not found",
                }
            ),
            404,
        )

    return jsonify(
        {
            "status": "ok",
        }
    )


@nutrition_api.post("/items")
@login_required
def api_add_item():
    data = request.get_json() or {}

    meal_id = data.get("meal_id")
    name = (data.get("name") or "").strip()

    if not meal_id or not name:
        return (
            jsonify(
                {
                    "error": "meal_id and name are required",
                }
            ),
            400,
        )

    item = add_item_service(
        current_user.id,
        {
            "meal_id": meal_id,
            "name": name,
            "weight": data.get("weight"),
            "calories": data.get("calories", 0),
            "protein": data.get("protein", 0),
            "fat": data.get("fat", 0),
            "carbs": data.get("carbs", 0),
            "fiber": data.get("fiber", 0),
            "category_label": data.get("category_label"),
            "category_id": data.get("category_id"),
        },
    )

    if item is None:
        return (
            jsonify(
                {
                    "error": "Meal not found",
                }
            ),
            404,
        )

    return (
        jsonify(
            {
                "status": "ok",
                "item_id": item.id,
            }
        ),
        201,
    )


@nutrition_api.put("/items/<int:item_id>")
@login_required
def api_edit_item(item_id):
    data = request.get_json() or {}

    item = update_item_service(
        current_user.id,
        item_id,
        data,
    )

    if item is None:
        return (
            jsonify(
                {
                    "error": "Item not found",
                }
            ),
            404,
        )

    return jsonify(
        {
            "status": "ok",
        }
    )


@nutrition_api.delete("/items/<int:item_id>")
@login_required
def api_delete_item(item_id):
    deleted = delete_item_service(
        current_user.id,
        item_id,
    )

    if not deleted:
        return (
            jsonify(
                {
                    "error": "Item not found",
                }
            ),
            404,
        )

    return jsonify(
        {
            "status": "ok",
        }
    )


@nutrition_api.post("/copy-yesterday")
@login_required
def api_copy_yesterday():
    yesterday = date.today() - timedelta(days=1)

    meals = Meal.query.filter_by(
        user_id=current_user.id,
        date=yesterday,
    ).all()

    if not meals:
        return (
            jsonify(
                {
                    "error": "No meals found yesterday",
                }
            ),
            400,
        )

    copied = []

    for meal in meals:
        new_meal = copy_meal_service(
            current_user.id,
            meal.id,
        )

        if new_meal:
            copied.append(new_meal.id)

    return jsonify(
        {
            "status": "ok",
            "copied": len(copied),
        }
    )


@nutrition_api.post("/weight")
@login_required
def api_update_weight():
    data = request.get_json() or {}

    try:
        weight = float(data.get("weight"))

    except (TypeError, ValueError):
        return (
            jsonify(
                {
                    "error": "Invalid weight",
                }
            ),
            400,
        )

    if weight <= 0:
        return (
            jsonify(
                {
                    "error": "Weight must be positive",
                }
            ),
            400,
        )

    entry = update_user_weight(
        current_user,
        weight,
    )

    return jsonify(
        {
            "status": "ok",
            "weight": entry.weight,
        }
    )


@nutrition_api.get("/weight")
@login_required
def api_get_weight():
    return jsonify(
        get_weight_data(
            current_user.id,
        )
    )


@nutrition_api.get("/stats")
@login_required
def api_stats():
    try:
        days = int(
            request.args.get(
                "days",
                7,
            )
        )

    except ValueError:
        days = 7

    days = max(
        1,
        min(days, 365),
    )

    data = get_stats(
        current_user.id,
        days,
    )

    return jsonify(data)


@nutrition_api.get("/heatmap")
@login_required
def api_heatmap():
    try:
        year = int(
            request.args.get(
                "year",
                date.today().year,
            )
        )

    except ValueError:
        year = date.today().year

    data = get_year_heatmap(
        current_user.id,
        year,
    )

    return jsonify(data)


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
        return (
            jsonify(
                {
                    "error": "Invalid amount",
                }
            ),
            400,
        )

    if amount <= 0:
        return (
            jsonify(
                {
                    "error": "Amount must be positive",
                }
            ),
            400,
        )

    entry = add_water_service(
        current_user.id,
        amount,
    )

    water_data = get_water_data(
        current_user.id,
    )

    return jsonify(
        {
            "status": "ok",
            "amount": water_data["amount"],
            "recommended": water_data["recommended"],
        }
    )
