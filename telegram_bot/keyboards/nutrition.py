from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


MEAL_CATEGORIES = {
    "breakfast": "🌅 Сніданок",
    "lunch": "☀️ Обід",
    "dinner": "🌙 Вечеря",
    "snack": "🍎 Перекус",
}

# Plain names (no emoji) for message text.
MEAL_NAMES = {
    "breakfast": "Сніданок",
    "lunch": "Обід",
    "dinner": "Вечеря",
    "snack": "Перекус",
}

# Older meals were stored with Ukrainian labels instead of keys.
_LEGACY_MEAL_CATEGORIES = {
    "сніданок": "breakfast",
    "обід": "lunch",
    "вечеря": "dinner",
    "перекус": "snack",
}


def normalize_meal_category(value: str | None) -> str | None:
    normalized = (value or "").strip().lower()
    if normalized in MEAL_CATEGORIES:
        return normalized
    return _LEGACY_MEAL_CATEGORIES.get(normalized)


def meal_name(value: str | None) -> str:
    category = normalize_meal_category(value)
    return MEAL_NAMES[category] if category else (value or "Прийом їжі")

CATALOG_LABELS = {
    "favorites": "⭐ Обрані",
    "recent": "🕘 Нещодавні",
    "mine": "👤 Мої продукти",
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
            [InlineKeyboardButton(text="🍽 Прийоми сьогодні", callback_data="nutrition:today")],
            [InlineKeyboardButton(text="👤 Мої продукти", callback_data="nutrition:catalog:mine")],
        ]
    )


def today_keyboard(meals: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for meal in meals:
        category = meal_name(meal.get("category") or meal.get("name"))
        time = meal.get("time")
        label = f"{category}" + (f" · {time}" if time else "")
        rows.append([
            InlineKeyboardButton(
                text=label[:40],
                callback_data=f"nutrition:meal_view:{meal['id']}",
            )
        ])
    rows.append([
        InlineKeyboardButton(text="➕ Додати їжу", callback_data="nutrition:add")
    ])
    rows.append([
        InlineKeyboardButton(text="← Назад", callback_data="nutrition:back")
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def meal_detail_keyboard(meal: dict) -> InlineKeyboardMarkup:
    rows = []
    for item in meal.get("items", []):
        name = item.get("name", "Продукт")
        rows.append([
            InlineKeyboardButton(
                text=f"✏️ {name[:24]}",
                callback_data=f"nutrition:entry_edit:{item['id']}",
            ),
            InlineKeyboardButton(
                text="🗑",
                callback_data=f"nutrition:entry_delete:{item['id']}",
            ),
        ])
    rows.append([
        InlineKeyboardButton(
            text="➕ Додати продукт",
            callback_data=f"nutrition:meal_add:{meal['id']}",
        )
    ])
    rows.append([
        InlineKeyboardButton(text="← Прийоми", callback_data="nutrition:today"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def meal_time_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏱ Поточний час", callback_data="nutrition:meal_time:now")],
            [InlineKeyboardButton(text="Пропустити", callback_data="nutrition:meal_time:skip")],
            [InlineKeyboardButton(text="✕ Скасувати", callback_data="nutrition:cancel")],
        ]
    )


def meal_categories() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=MEAL_CATEGORIES["breakfast"],
                    callback_data="nutrition:meal:breakfast",
                ),
                InlineKeyboardButton(
                    text=MEAL_CATEGORIES["lunch"],
                    callback_data="nutrition:meal:lunch",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=MEAL_CATEGORIES["dinner"],
                    callback_data="nutrition:meal:dinner",
                ),
                InlineKeyboardButton(
                    text=MEAL_CATEGORIES["snack"],
                    callback_data="nutrition:meal:snack",
                ),
            ],
            [InlineKeyboardButton(text="← Назад", callback_data="nutrition:back"), InlineKeyboardButton(text="✕ Скасувати", callback_data="nutrition:cancel")],
        ]
    )


def catalog_keyboard(mode: str = "search") -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="🔎 Знайти продукт", callback_data="nutrition:search"),
            InlineKeyboardButton(text="⭐ Обрані", callback_data="nutrition:catalog:favorites"),
        ],
        [
            InlineKeyboardButton(text="🕘 Нещодавні", callback_data="nutrition:catalog:recent"),
            InlineKeyboardButton(text="👤 Мої продукти", callback_data="nutrition:catalog:mine"),
        ],
        [
            InlineKeyboardButton(text="➕ Додати свій продукт", callback_data="nutrition:my-product"),
        ],
        [InlineKeyboardButton(text="← Назад", callback_data="nutrition:product_menu"), InlineKeyboardButton(text="✕ Скасувати", callback_data="nutrition:cancel")],
    ]
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
        row = [
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
        if product.get("is_own"):
            row.append(
                InlineKeyboardButton(
                    text="✏️",
                    callback_data=f"nutrition:myprod:{product['id']}",
                )
            )
        rows.append(row)

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
            text="← Назад",
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


# Fields of the user's own product that can be edited from the bot.
PRODUCT_FIELDS = {
    "name": "Назва",
    "kcal_per_100g": "Ккал",
    "protein_per_100g": "Білки",
    "fat_per_100g": "Жири",
    "carbs_per_100g": "Вуглеводи",
}


def my_product_keyboard(product_id: int) -> InlineKeyboardMarkup:
    field = lambda key: InlineKeyboardButton(  # noqa: E731
        text=PRODUCT_FIELDS[key],
        callback_data=f"nutrition:myprod_edit:{product_id}:{key}",
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [field("name"), field("kcal_per_100g")],
            [field("protein_per_100g"), field("fat_per_100g"), field("carbs_per_100g")],
            [InlineKeyboardButton(text="🗑 Видалити продукт", callback_data=f"nutrition:myprod_delete:{product_id}")],
            [InlineKeyboardButton(text="← Мої продукти", callback_data="nutrition:catalog:mine")],
        ]
    )


def my_product_delete_keyboard(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Так, видалити", callback_data=f"nutrition:myprod_delete_yes:{product_id}"),
                InlineKeyboardButton(text="Ні", callback_data=f"nutrition:myprod:{product_id}"),
            ]
        ]
    )


def my_product_edit_cancel_keyboard(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="← Назад до продукту", callback_data=f"nutrition:myprod:{product_id}")]
        ]
    )
