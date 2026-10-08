from telegram_bot.keyboards.nutrition import normalize_meal_category
from telegram_bot.services.api import NosiFitAPI


def meal_by_category(day: dict, category: str) -> dict | None:
    wanted = normalize_meal_category(category)
    for meal in day.get("meals", []):
        if normalize_meal_category(meal.get("category") or meal.get("name")) == wanted:
            return meal
    return None


def get_or_create_meal(api: NosiFitAPI, day: dict, category: str, time: str | None = None) -> dict:
    existing = meal_by_category(day, category)
    if existing is not None:
        return existing
    key = normalize_meal_category(category) or category
    return api.create_meal(name=key, category=key, time=time)
