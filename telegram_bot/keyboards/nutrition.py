from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


MEAL_CATEGORIES = {
    "breakfast": "🌅 Сніданок",
    "lunch": "☀️ Обід",
    "dinner": "🌙 Вечеря",
    "snack": "🍎 Перекус",
}

CATALOG_LABELS = {
    "all": "📚 Усі",
    "favorites": "⭐ Обрані",
    "recent": "🕘 Останні",
    "mine": "👤 Мої",
}

UNIT_LABELS = {
    "g": "г",
    "ml": "мл",
    "pcs": "шт.",
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
                InlineKeyboardButton(
                    text=MEAL_CATEGORIES["breakfast"],
                    callback_data="nutrition:meal:Сніданок",
                ),
                InlineKeyboardButton(
                    text=MEAL_CATEGORIES["lunch"],
                    callback_data="nutrition:meal:Обід",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=MEAL_CATEGORIES["dinner"],
                    callback_data="nutrition:meal:Вечеря",
                ),
                InlineKeyboardButton(
                    text=MEAL_CATEGORIES["snack"],
                    callback_data="nutrition:meal:Перекус",
                ),
            ],
            [InlineKeyboardButton(text="✕ Скасувати", callback_data="nutrition:cancel")],
        ]
    )


def catalog_keyboard(mode: str = "all") -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=("• " if mode == "all" else "") + CATALOG_LABELS["all"],
                callback_data="nutrition:catalog:all",
            ),
            InlineKeyboardButton(
                text=("• " if mode == "favorites" else "") + CATALOG_LABELS["favorites"],
                callback_data="nutrition:catalog:favorites",
            ),
        ],
        [
            InlineKeyboardButton(
                text=("• " if mode == "recent" else "") + CATALOG_LABELS["recent"],
                callback_data="nutrition:catalog:recent",
            ),
            InlineKeyboardButton(
                text=("• " if mode == "mine" else "") + CATALOG_LABELS["mine"],
                callback_data="nutrition:catalog:mine",
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔎 Пошук",
                callback_data="nutrition:search",
            ),
            InlineKeyboardButton(
                text="➕ Мій продукт",
                callback_data="nutrition:my-product",
            ),
        ],
        [InlineKeyboardButton(text="✕ Скасувати", callback_data="nutrition:cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def product_results(
    products: list[dict],
    *,
    mode: str = "all",
    query: str = "",
) -> InlineKeyboardMarkup:
    rows = []
    for product in products[:8]:
        favorite = "★" if product.get("is_favorite") else "☆"
        rows.append(
            [
                InlineKeyboardButton(
                    text=product["name"][:40],
                    callback_data=f"nutrition:product:{product['id']}",
                ),
                InlineKeyboardButton(
                    text=favorite,
                    callback_data=(
                        f"nutrition:fav:{product['id']}:"
                        f"{0 if product.get('is_favorite') else 1}"
                    ),
                ),
            ]
        )

    if query:
        rows.append(
            [InlineKeyboardButton(text="🔎 Новий пошук", callback_data="nutrition:search")]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text="← Каталог",
                callback_data=f"nutrition:catalog:{mode}",
            ),
            InlineKeyboardButton(
                text="✕ Скасувати",
                callback_data="nutrition:cancel",
            ),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def amount_keyboard(unit: str) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=("• " if unit == current else "") + UNIT_LABELS[current],
                callback_data=f"nutrition:unit:{current}",
            )
            for current in ("g", "ml", "pcs")
        ],
        [InlineKeyboardButton(text="✕ Скасувати", callback_data="nutrition:cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def review_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Додати ще",
                    callback_data="nutrition:more",
                ),
                InlineKeyboardButton(
                    text="💾 Зберегти",
                    callback_data="nutrition:save",
                ),
            ],
            [InlineKeyboardButton(text="✕ Скасувати", callback_data="nutrition:cancel")],
        ]
    )


def my_product_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✕ Скасувати", callback_data="nutrition:cancel")]
        ]
    )
