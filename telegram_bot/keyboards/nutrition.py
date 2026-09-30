from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


MEAL_CATEGORIES = {
    "breakfast": "🌅 Сніданок",
    "lunch": "☀️ Обід",
    "dinner": "🌙 Вечеря",
    "snack": "🍎 Перекус",
}


def nutrition_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Додати їжу", callback_data="nutrition:add")],
            [InlineKeyboardButton(text="📊 Сьогодні", callback_data="nutrition:today")],
        ]
    )


def meal_categories() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=MEAL_CATEGORIES["breakfast"], callback_data="nutrition:meal:Сніданок"),
                InlineKeyboardButton(text=MEAL_CATEGORIES["lunch"], callback_data="nutrition:meal:Обід"),
            ],
            [
                InlineKeyboardButton(text=MEAL_CATEGORIES["dinner"], callback_data="nutrition:meal:Вечеря"),
                InlineKeyboardButton(text=MEAL_CATEGORIES["snack"], callback_data="nutrition:meal:Перекус"),
            ],
            [InlineKeyboardButton(text="✕ Скасувати", callback_data="nutrition:cancel")],
        ]
    )


def product_results(products: list[dict]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=product["name"][:48], callback_data=f"nutrition:product:{product['id']}")]
        for product in products
    ]
    rows.append([InlineKeyboardButton(text="✕ Скасувати", callback_data="nutrition:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def review_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Додати ще", callback_data="nutrition:more"),
                InlineKeyboardButton(text="💾 Зберегти", callback_data="nutrition:save"),
            ],
            [InlineKeyboardButton(text="✕ Скасувати", callback_data="nutrition:cancel")],
        ]
    )
