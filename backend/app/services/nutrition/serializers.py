from backend.app.services.nutrition.meal_categories import normalize_meal_category
from backend.app.services.nutrition.product_service import (
    get_product_name,
)


def serialize_meal(meal, locale="uk"):
    category = normalize_meal_category(meal.category) or meal.category

    return {
        "id": meal.id,
        "name": category,
        "category": category,
        "date": meal.date.isoformat() if meal.date else None,
        "time": meal.time.strftime("%H:%M") if meal.time else None,
        "total_calories": meal.total_calories,
        "total_protein": meal.total_protein,
        "total_fat": meal.total_fat,
        "total_carbs": meal.total_carbs,
        "total_fiber": meal.total_fiber,
        "items": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "name": (
                    get_product_name(item.product, locale)
                    if item.product is not None
                    else item.name
                ),
                "amount": item.amount,
                "unit": item.unit,
                "weight": item.weight,
                "calories": item.calories,
                "protein": item.protein,
                "fat": item.fat,
                "carbs": item.carbs,
                "fiber": item.fiber,
                "liquid_ml": item.liquid_ml,
            }
            for item in meal.items
        ],
    }
