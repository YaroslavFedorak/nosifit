from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


MEAL_CATEGORIES = {
    "breakfast": "🌅 Сніданок",
    "lunch": "☀️ Обід",
    "dinner": "🌙 Вечеря",
    "snack": "🍎 Перекус",
}

CATALOG_LABELS = {
    "favorites": "⭐ Обрані",
    "recent": "🕘 Недавні",
    "mine": "👤 Мої",
}

PRODUCT_CATEGORIES = {
    "meat": "🥩 М'ясо",
    "fish": "🐟 Риба",
    "dairy": "🥛 Молочні",
    "eggs": "🥚 Яйця",
    "grains": "🌾 Крупи та паста",
    "bread": "🥖 Хліб",
    "vegetables": "🥦 Овочі",
    "fruits": "🍎 Фрукти",
    "legumes": "🫘 Бобові",
    "nuts": "🥜 Горіхи",
    "oils": "🫒 Олії",
    "sweets": "🍫 Солодке",
    "beverages": "🥤 Напої",
    "other": "📦 Інше",
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


def catalog_keyboard(mode: str = "search") -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="🔎 Пошук продукту", callback_data="nutrition:search"),
            InlineKeyboardButton(text="⭐ Обрані", callback_data="nutrition:catalog:favorites"),
        ],
        [
            InlineKeyboardButton(text="🕘 Недавні", callback_data="nutrition:catalog:recent"),
            InlineKeyboardButton(text="📂 Категорії", callback_data="nutrition:categories"),
        ],
        [
            InlineKeyboardButton(text="👤 Мої продукти", callback_data="nutrition:catalog:mine"),
            InlineKeyboardButton(text="➕ Мій продукт", callback_data="nutrition:my-product"),
        ],
        [InlineKeyboardButton(text="✕ Скасувати", callback_data="nutrition:cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def category_keyboard() -> InlineKeyboardMarkup:
    keys = list(PRODUCT_CATEGORIES)
    rows = []
    for index in range(0, len(keys), 2):
        row = [
            InlineKeyboardButton(
                text=PRODUCT_CATEGORIES[key],
                callback_data=f"nutrition:category:{key}",
            )
            for key in keys[index:index + 2]
        ]
        rows.append(row)
    rows.append([
        InlineKeyboardButton(text="← Назад", callback_data="nutrition:product_menu"),
        InlineKeyboardButton(text="✕ Скасувати", callback_data="nutrition:cancel"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def product_results(
    products: list[dict],
    *,
    mode: str = "search",
    query: str = "",
    category: str = "",
    offset: int = 0,
    has_more: bool = False,
) -> InlineKeyboardMarkup:
    rows = []
    page = products[offset:offset + 8]
    for product in page:
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

    if has_more:
        rows.append([
            InlineKeyboardButton(
                text="Показати ще",
                callback_data=f"nutrition:more_results:{offset + 8}",
            )
        ])

    if query:
        rows.append([
            InlineKeyboardButton(text="🔎 Новий пошук", callback_data="nutrition:search")
        ])
    rows.append([
        InlineKeyboardButton(
            text="← Каталог",
            callback_data="nutrition:product_menu",
        ),
        InlineKeyboardButton(text="✕ Скасувати", callback_data="nutrition:cancel"),
    ])
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


def review_keyboard(pending: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for index, item in enumerate(pending):
        name = item.get("name", "Продукт")
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"✏️ {name[:28]}",
                    callback_data=f"nutrition:edit:{index}",
                ),
                InlineKeyboardButton(
                    text="🗑",
                    callback_data=f"nutrition:delete:{index}",
                ),
            ]
        )

    action_row = [
        InlineKeyboardButton(
            text="➕ Додати ще",
            callback_data="nutrition:more",
        ),
    ]
    if pending:
        action_row.append(
            InlineKeyboardButton(
                text="✅ Зберегти",
                callback_data="nutrition:save",
            )
        )
    rows.append(action_row)
    rows.append(
        [InlineKeyboardButton(text="✕ Скасувати", callback_data="nutrition:cancel")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def my_product_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✕ Скасувати", callback_data="nutrition:cancel")]
        ]
    )
