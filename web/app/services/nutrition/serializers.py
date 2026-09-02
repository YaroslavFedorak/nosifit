def serialize_meal(meal):
    return {
        "id": meal.id,
        "name": meal.name,
        "category": meal.category,
        "time": meal.time.strftime("%H:%M") if meal.time else None,
        "total_calories": meal.total_calories,
        "total_protein": meal.total_protein,
        "total_fat": meal.total_fat,
        "total_carbs": meal.total_carbs,
        "items": [
            {
                "id": item.id,
                "name": item.name,
                "calories": item.calories,
                "protein": item.protein,
                "fat": item.fat,
                "carbs": item.carbs,
                "fiber": item.fiber,
            }
            for item in meal.items
        ],
    }
