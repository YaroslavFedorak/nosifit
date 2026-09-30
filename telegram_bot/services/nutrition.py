from telegram_bot.services.api import NosiFitAPI


def meal_by_category(day: dict, category: str) -> dict | None:
    for meal in day.get("meals", []):
        if meal.get("category") == category:
            return meal
    return None


def get_or_create_meal(api: NosiFitAPI, day: dict, category: str) -> dict:
    existing = meal_by_category(day, category)
    if existing is not None:
        return existing
    return api.create_meal(name=category, category=category)
