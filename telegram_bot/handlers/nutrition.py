import asyncio
import html
import re

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from telegram_bot.keyboards.main import NUTRITION, main_menu
from telegram_bot.keyboards.nutrition import (
    CATALOG_LABELS,
    UNIT_LABELS,
    amount_keyboard,
    catalog_keyboard,
    meal_categories,
    my_product_cancel_keyboard,
    nutrition_menu,
    product_results,
    review_keyboard,
)
from telegram_bot.services.api import NosiFitAPIError
from telegram_bot.services.nutrition import get_or_create_meal
from telegram_bot.states.nutrition import NutritionStates


router = Router()
CATALOG_LIMIT = 50
SEARCH_LIMIT = 8


def _api(user_id: int):
    from telegram_bot.runtime import get_api
    return get_api(user_id)


def _format_number(value: float) -> str:
    return f"{value:.1f}".rstrip("0").rstrip(".")


def _parse_amount(text: str) -> float | None:
    match = re.search(r"\d+(?:[.,]\d+)?", text)
    if not match:
        return None
    value = float(match.group().replace(",", "."))
    return value if value > 0 else None


def _format_day(day: dict) -> str:
    progress = day.get("progress", {})
    goals = day.get("goals", {})
    return (
        "🍽 <b>Харчування сьогодні</b>\n\n"
        f"🔥 {progress.get('calories', 0):.0f} / {goals.get('calories', 0):.0f} kcal\n"
        f"🥩 {progress.get('protein', 0):.1f} / {goals.get('protein', 0):.1f} г білка\n"
        f"🥑 {progress.get('fat', 0):.1f} / {goals.get('fat', 0):.1f} г жирів\n"
        f"🍞 {progress.get('carbs', 0):.1f} / {goals.get('carbs', 0):.1f} г вуглеводів\n\n"
        f"Прийомів їжі: {len(day.get('meals', []))}"
    )


def _meal_by_category(day: dict, category: str) -> dict | None:
    return next(
        (meal for meal in day.get("meals", []) if meal.get("category") == category),
        None,
    )


def _format_product(product: dict) -> str:
    unit = UNIT_LABELS.get(product.get("default_unit", "g"), product.get("default_unit", "g"))
    return (
        f"🍽 <b>{html.escape(product.get('name', 'Продукт'))}</b>\n\n"
        f"🔥 {product.get('kcal_per_100g', 0):.0f} kcal / 100 г\n"
        f"🥩 {product.get('protein_per_100g', 0):.1f} г білка · "
        f"🥑 {product.get('fat_per_100g', 0):.1f} г жирів\n"
        f"🍞 {product.get('carbs_per_100g', 0):.1f} г вуглеводів\n\n"
        f"Одиниця за замовчуванням: <b>{unit}</b>"
    )


def _format_catalog(mode: str, products: list[dict], query: str = "") -> str:
    title = CATALOG_LABELS.get(mode, CATALOG_LABELS["all"])
    suffix = f' для «{html.escape(query)}»' if query else ""
    if not products:
        return (
            f"🍽 <b>{title}</b>{suffix}\n\n"
            "Нічого не знайдено. Спробуйте інший запит."
        )
    return (
        f"🍽 <b>{title}</b>{suffix}\n\n"
        "Оберіть продукт. ☆ / ★ — обране."
    )


def _pending_totals(pending: list[dict]) -> tuple[float, float, float, float]:
    calories = protein = fat = carbs = 0.0
    for item in pending:
        amount = float(item["amount"])
        unit = item["unit"]
        grams_per_unit = float(item.get("grams_per_unit") or 1)
        grams = amount if unit == "g" else amount * grams_per_unit
        factor = grams / 100.0
        calories += float(item.get("kcal_per_100g") or 0) * factor
        protein += float(item.get("protein_per_100g") or 0) * factor
        fat += float(item.get("fat_per_100g") or 0) * factor
        carbs += float(item.get("carbs_per_100g") or 0) * factor
    return calories, protein, fat, carbs


def _format_pending(
    category: str,
    pending: list[dict],
    existing: list[dict] | None = None,
) -> str:
    lines = [f"🍽 <b>{html.escape(category)}</b>"]
    existing = existing or []
    if existing:
        lines.extend(["", "У прийомі вже є:"])
        for item in existing:
            unit = UNIT_LABELS.get(item.get("unit", "g"), item.get("unit", "g"))
            lines.append(
                f"• {html.escape(item.get('name', 'Продукт'))} — "
                f"{_format_number(float(item.get('amount') or item.get('weight') or 0))} {unit}"
            )
    if pending:
        lines.extend(["", "Чернетка:"])
        for index, item in enumerate(pending, start=1):
            unit = UNIT_LABELS.get(item["unit"], item["unit"])
            lines.append(
                f"{index}. {html.escape(item['name'])} — "
                f"{_format_number(item['amount'])} {unit}"
            )
        calories, protein, fat, carbs = _pending_totals(pending)
        lines.extend([
            "",
            "<b>Підсумок чернетки</b>",
            f"🔥 {calories:.0f} kcal",
            f"🥩 {protein:.1f} г білка · 🥑 {fat:.1f} г жирів",
            f"🍞 {carbs:.1f} г вуглеводів",
        ])
    return "\n".join(lines)


async def _load_catalog(
    user_id: int,
    state: FSMContext,
    mode: str,
) -> list[dict]:
    api = _api(user_id)
    loaders = {
        "all": api.get_products,
        "favorites": api.get_favorite_products,
        "recent": api.get_recent_products,
        "mine": api.get_my_products,
    }
    loader = loaders[mode]
    products = await asyncio.to_thread(loader, "uk", CATALOG_LIMIT)
    data = await state.get_data()
    catalogs = dict(data.get("catalogs", {}))
    catalogs[mode] = products
    await state.update_data(catalogs=catalogs, catalog_mode=mode)
    return products


async def _show_catalog(
    callback: CallbackQuery,
    state: FSMContext,
    mode: str,
    *,
    query: str = "",
) -> None:
    data = await state.get_data()
    catalogs = data.get("catalogs", {})
    products = catalogs.get(mode)

    if products is None:
        try:
            products = await _load_catalog(callback.from_user.id, state, mode)
        except NosiFitAPIError as exc:
            await callback.message.answer(f"Не вдалося завантажити каталог: {exc}")
            return

    matches = products[:SEARCH_LIMIT] if query else products
    await state.set_state(
        NutritionStates.searching_product if query else NutritionStates.browsing_catalog
    )
    await _safe_edit(
        callback.message,
        _format_catalog(mode, matches, query),
        reply_markup=product_results(matches, mode=mode, query=query),
    )


async def _safe_edit(message: Message, text: str, *, reply_markup=None) -> None:
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc).lower():
            raise


async def _start_product_search(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(NutritionStates.searching_product)
    data = await state.get_data()
    mode = data.get("catalog_mode", "all")
    await _safe_edit(
        callback.message,
        f"🔎 <b>Пошук продукту</b>\n\n"
        f"Каталог: <b>{CATALOG_LABELS.get(mode, 'Усі')}</b>\n"
        "Напишіть назву продукту. Результати з'являться одразу після повідомлення.",
        reply_markup=catalog_keyboard(mode),
    )


@router.message(F.text == NUTRITION)
async def nutrition(message: Message, state: FSMContext) -> None:
    await state.clear()
    try:
        day = await asyncio.to_thread(_api(message.from_user.id).get_day)
    except NosiFitAPIError as exc:
        await message.answer(
            f"Не вдалося підключитися до NosiFit: {exc}",
            reply_markup=main_menu(authenticated=True),
        )
        return
    await message.answer(_format_day(day), reply_markup=nutrition_menu())


@router.callback_query(F.data == "nutrition:add")
async def add_food(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await state.set_state(NutritionStates.choosing_meal)
    await callback.message.edit_text(
        "🍽 <b>Додати їжу</b>\n\nОберіть прийом їжі:",
        reply_markup=meal_categories(),
    )


@router.callback_query(
    NutritionStates.choosing_meal,
    F.data.startswith("nutrition:meal:"),
)
async def choose_meal(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    category = callback.data.split(":", 2)[2]
    try:
        day = await asyncio.to_thread(_api(callback.from_user.id).get_day)
    except NosiFitAPIError as exc:
        await callback.message.answer(f"Не вдалося завантажити дані: {exc}")
        return

    meal = _meal_by_category(day, category)
    await state.update_data(
        category=category,
        meal_id=meal.get("id", 0) if meal else 0,
        existing_items=meal.get("items", []) if meal else [],
        pending=[],
        catalogs={},
        catalog_mode="all",
    )
    await _show_catalog(callback, state, "all")


@router.callback_query(
    F.data.startswith("nutrition:catalog:"),
)
async def switch_catalog(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    mode = callback.data.rsplit(":", 1)[1]
    if mode not in CATALOG_LABELS:
        return
    await _show_catalog(callback, state, mode)


@router.callback_query(F.data == "nutrition:search")
async def search_button(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _start_product_search(callback, state)


@router.message(NutritionStates.browsing_catalog)
async def browse_catalog_text(message: Message, state: FSMContext) -> None:
    await _handle_product_query(message, state)


@router.message(NutritionStates.searching_product)
async def search_product(message: Message, state: FSMContext) -> None:
    await _handle_product_query(message, state)


async def _handle_product_query(message: Message, state: FSMContext) -> None:
    query = (message.text or "").strip()
    if not query:
        await message.answer("Введіть назву продукту.")
        return

    data = await state.get_data()
    mode = data.get("catalog_mode", "all")

    try:
        matches = await asyncio.to_thread(
            _api(message.from_user.id).search_products,
            query,
            "uk",
            SEARCH_LIMIT,
        )
    except NosiFitAPIError as exc:
        await message.answer(f"Не вдалося виконати пошук: {exc}")
        return

    catalogs = dict(data.get("catalogs", {}))
    catalogs[mode] = matches
    await state.update_data(catalogs=catalogs)
    await state.set_state(NutritionStates.searching_product)
    if not matches:
        await message.answer(
            f"🔎 <b>{html.escape(query)}</b>\n\n"
            "Нічого не знайдено. Спробуйте коротшу назву або інший каталог.",
            reply_markup=catalog_keyboard(mode),
        )
        return

    await message.answer(
        _format_catalog(mode, matches, query),
        reply_markup=product_results(matches, mode=mode, query=query),
    )


@router.callback_query(
    F.data.startswith("nutrition:fav:"),
)
async def toggle_favorite(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    _, _, product_id, value = callback.data.split(":")
    try:
        await asyncio.to_thread(
            _api(callback.from_user.id).set_product_favorite,
            int(product_id),
            value == "1",
        )
        data = await state.get_data()
        mode = data.get("catalog_mode", "all")
        catalogs = dict(data.get("catalogs", {}))
        catalogs.pop(mode, None)
        await state.update_data(catalogs=catalogs)
        await _show_catalog(callback, state, mode)
    except NosiFitAPIError as exc:
        await callback.message.answer(f"Не вдалося змінити обране: {exc}")


@router.callback_query(
    F.data.startswith("nutrition:product:"),
)
async def choose_product(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    product_id = int(callback.data.rsplit(":", 1)[1])
    data = await state.get_data()
    catalogs = data.get("catalogs", {})
    product = next(
        (
            product
            for products in catalogs.values()
            for product in products
            if product.get("id") == product_id
        ),
        None,
    )

    if product is None:
        try:
            product = await asyncio.to_thread(
                _api(callback.from_user.id).get_product,
                product_id,
            )
        except NosiFitAPIError as exc:
            await callback.message.answer(f"Не вдалося завантажити продукт: {exc}")
            return

    unit = product.get("default_unit") or "g"
    default_amount = 1 if unit == "pcs" else 100
    await state.update_data(
        product_id=product_id,
        product_name=product.get("name", "Продукт"),
        product_unit=unit,
        product_kcal_per_100g=product.get("kcal_per_100g", 0),
        product_protein_per_100g=product.get("protein_per_100g", 0),
        product_fat_per_100g=product.get("fat_per_100g", 0),
        product_carbs_per_100g=product.get("carbs_per_100g", 0),
        product_grams_per_unit=product.get("grams_per_unit", 1),
    )
    await state.set_state(NutritionStates.entering_amount)
    await callback.message.edit_text(
        _format_product(product)
        + "\n\n"
        f"Введіть кількість у <b>{UNIT_LABELS.get(unit, unit)}</b>. "
        f"За замовчуванням: <b>{default_amount:g}</b>.",
        reply_markup=amount_keyboard(unit),
    )


@router.callback_query(
    NutritionStates.entering_amount,
    F.data.startswith("nutrition:unit:"),
)
async def choose_unit(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    unit = callback.data.rsplit(":", 1)[1]
    if unit not in UNIT_LABELS:
        return
    await state.update_data(product_unit=unit)
    data = await state.get_data()
    default_amount = 1 if unit == "pcs" else 100
    await _safe_edit(
        callback.message,
        f"🍽 <b>{html.escape(data.get('product_name', 'Продукт'))}</b>\n\n"
        f"Введіть кількість у <b>{UNIT_LABELS[unit]}</b>. "
        f"За замовчуванням: <b>{default_amount:g}</b>.",
        reply_markup=amount_keyboard(unit),
    )


@router.message(NutritionStates.entering_amount)
async def enter_amount(message: Message, state: FSMContext) -> None:
    amount = _parse_amount(message.text or "")
    if amount is None:
        await message.answer("Введіть додатне число, наприклад 150 або 1,5.")
        return

    data = await state.get_data()
    pending = list(data.get("pending", []))
    item = {
        "product_id": data["product_id"],
        "name": data["product_name"],
        "amount": amount,
        "unit": data["product_unit"],
        "kcal_per_100g": data.get("product_kcal_per_100g", 0),
        "protein_per_100g": data.get("product_protein_per_100g", 0),
        "fat_per_100g": data.get("product_fat_per_100g", 0),
        "carbs_per_100g": data.get("product_carbs_per_100g", 0),
        "grams_per_unit": data.get("product_grams_per_unit", 1),
    }
    editing_index = data.get("editing_index")
    if editing_index is not None and 0 <= int(editing_index) < len(pending):
        pending[int(editing_index)] = item
    else:
        pending.append(item)
    await state.update_data(pending=pending, editing_index=None)
    await state.set_state(NutritionStates.reviewing)
    await message.answer(
        _format_pending(
            data["category"],
            pending,
            data.get("existing_items", []),
        ),
        reply_markup=review_keyboard(pending),
    )


@router.callback_query(
    NutritionStates.reviewing,
    F.data.startswith("nutrition:edit:"),
)
async def edit_pending_item(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    index = int(callback.data.rsplit(":", 1)[1])
    data = await state.get_data()
    pending = list(data.get("pending", []))
    if index < 0 or index >= len(pending):
        await callback.message.answer("Цю позицію вже видалено.")
        return

    item = pending[index]
    await state.update_data(
        editing_index=index,
        product_id=item["product_id"],
        product_name=item["name"],
        product_unit=item["unit"],
        product_kcal_per_100g=item.get("kcal_per_100g", 0),
        product_protein_per_100g=item.get("protein_per_100g", 0),
        product_fat_per_100g=item.get("fat_per_100g", 0),
        product_carbs_per_100g=item.get("carbs_per_100g", 0),
        product_grams_per_unit=item.get("grams_per_unit", 1),
    )
    await state.set_state(NutritionStates.entering_amount)
    await _safe_edit(
        callback.message,
        f"✏️ <b>{html.escape(item['name'])}</b>\n\n"
        f"Поточна кількість: <b>{_format_number(item['amount'])} "
        f"{UNIT_LABELS.get(item['unit'], item['unit'])}</b>\n"
        f"Введіть нову кількість.",
        reply_markup=amount_keyboard(item["unit"]),
    )


@router.callback_query(
    NutritionStates.reviewing,
    F.data.startswith("nutrition:delete:"),
)
async def delete_pending_item(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    index = int(callback.data.rsplit(":", 1)[1])
    data = await state.get_data()
    pending = list(data.get("pending", []))
    if index < 0 or index >= len(pending):
        await callback.message.answer("Цю позицію вже видалено.")
        return

    pending.pop(index)
    await state.update_data(pending=pending)
    if not pending:
        await _safe_edit(
            callback.message,
            f"🍽 <b>{html.escape(data['category'])}</b>\n\n"
            "Чернетка порожня. Додайте продукт або скасуйте.",
            reply_markup=review_keyboard(pending),
        )
        return

    await _safe_edit(
        callback.message,
        _format_pending(data["category"], pending, data.get("existing_items", [])),
        reply_markup=review_keyboard(pending),
    )


@router.callback_query(NutritionStates.reviewing, F.data == "nutrition:more")
async def add_more(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(NutritionStates.searching_product)
    data = await state.get_data()
    mode = data.get("catalog_mode", "all")
    await _safe_edit(
        callback.message,
        f"🍽 <b>{html.escape(data['category'])}</b>\n\n"
        "Напишіть назву наступного продукту.",
        reply_markup=catalog_keyboard(mode),
    )


@router.callback_query(NutritionStates.reviewing, F.data == "nutrition:save")
async def save_meal(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = await state.get_data()
    await state.set_state(NutritionStates.saving)
    pending = data.get("pending", [])
    category = data["category"]

    if not pending:
        await callback.message.answer("У прийомі ще немає нових продуктів.")
        return

    try:
        api = _api(callback.from_user.id)
        meal_id = int(data.get("meal_id") or 0)
        if not meal_id:
            day = await asyncio.to_thread(api.get_day)
            meal = await asyncio.to_thread(get_or_create_meal, api, day, category)
            meal_id = meal["id"]

        await asyncio.to_thread(
            api.add_entries,
            meal_id,
            [
                {
                    "product_id": item["product_id"],
                    "amount": item["amount"],
                    "unit": item["unit"],
                }
                for item in pending
            ],
        )
        updated_day = await asyncio.to_thread(api.get_day)
    except NosiFitAPIError as exc:
        await state.set_state(NutritionStates.reviewing)
        await callback.message.answer(
            f"Не вдалося зберегти прийом: {exc}\n\n"
            "Чернетку збережено. Спробуйте ще раз."
        )
        return

    await state.clear()
    await _safe_edit(
        callback.message,
        "✅ <b>Прийом їжі збережено</b>\n\n" + _format_day(updated_day),
        reply_markup=nutrition_menu(),
    )


@router.callback_query(F.data == "nutrition:today")
async def today(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    try:
        day = await asyncio.to_thread(_api(callback.from_user.id).get_day)
    except NosiFitAPIError as exc:
        await callback.message.answer(f"Не вдалося завантажити дані: {exc}")
        return
    await _safe_edit(callback.message, _format_day(day), reply_markup=nutrition_menu())


@router.callback_query(F.data == "nutrition:my-product")
async def my_product_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(NutritionStates.product_name)
    await callback.message.edit_text(
        "➕ <b>Мій продукт</b>\n\n"
        "Введіть назву продукту:",
        reply_markup=my_product_cancel_keyboard(),
    )


@router.message(NutritionStates.product_name)
async def my_product_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name:
        await message.answer("Введіть назву продукту.")
        return
    await state.update_data(new_product_name=name)
    await state.set_state(NutritionStates.product_kcal)
    await message.answer("Введіть калорійність на 100 г, наприклад <b>250</b>.")


async def _read_product_number(
    message: Message,
    state: FSMContext,
    next_state: NutritionStates,
    key: str,
    prompt: str,
) -> None:
    value = _parse_amount(message.text or "")
    if value is None:
        await message.answer("Введіть додатне число.")
        return
    await state.update_data(**{key: value})
    await state.set_state(next_state)
    await message.answer(prompt)


@router.message(NutritionStates.product_kcal)
async def my_product_kcal(message: Message, state: FSMContext) -> None:
    await _read_product_number(
        message,
        state,
        NutritionStates.product_protein,
        "new_product_kcal",
        "Введіть білок на 100 г.",
    )


@router.message(NutritionStates.product_protein)
async def my_product_protein(message: Message, state: FSMContext) -> None:
    await _read_product_number(
        message,
        state,
        NutritionStates.product_fat,
        "new_product_protein",
        "Введіть жири на 100 г.",
    )


@router.message(NutritionStates.product_fat)
async def my_product_fat(message: Message, state: FSMContext) -> None:
    await _read_product_number(
        message,
        state,
        NutritionStates.product_carbs,
        "new_product_fat",
        "Введіть вуглеводи на 100 г.",
    )


@router.message(NutritionStates.product_carbs)
async def my_product_carbs(message: Message, state: FSMContext) -> None:
    value = _parse_amount(message.text or "")
    if value is None:
        await message.answer("Введіть додатне число.")
        return
    data = await state.get_data()
    try:
        product = await asyncio.to_thread(
            _api(message.from_user.id).create_product,
            {
                "name": data["new_product_name"],
                "kcal_per_100g": data["new_product_kcal"],
                "protein_per_100g": data["new_product_protein"],
                "fat_per_100g": data["new_product_fat"],
                "carbs_per_100g": value,
                "fiber_per_100g": 0,
                "default_unit": "g",
                "grams_per_unit": 1,
            },
        )
    except NosiFitAPIError as exc:
        await message.answer(f"Не вдалося створити продукт: {exc}")
        return

    await state.update_data(
        product_id=product["id"],
        product_name=product["name"],
        product_unit=product.get("default_unit", "g"),
        product_kcal_per_100g=product.get("kcal_per_100g", data["new_product_kcal"]),
        product_protein_per_100g=product.get("protein_per_100g", data["new_product_protein"]),
        product_fat_per_100g=product.get("fat_per_100g", data["new_product_fat"]),
        product_carbs_per_100g=product.get("carbs_per_100g", value),
        product_grams_per_unit=product.get("grams_per_unit", 1),
        new_product_carbs=value,
    )
    await state.set_state(NutritionStates.entering_amount)
    await message.answer(
        _format_product(product)
        + "\n\nВведіть кількість у <b>г</b>. За замовчуванням: <b>100</b>.",
        reply_markup=amount_keyboard("g"),
    )


@router.callback_query(F.data == "nutrition:cancel")
async def cancel_nutrition(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await _safe_edit(callback.message, "Дію скасовано.")
    await callback.message.answer(
        "Оберіть дію:",
        reply_markup=main_menu(authenticated=True),
    )
