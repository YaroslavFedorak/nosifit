import asyncio
import html
import io
import re

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from telegram_bot.keyboards.main import FOOD, NUTRITION, nutrition_mode_menu
from telegram_bot.keyboards.nutrition import (
    CATALOG_LABELS,
    UNIT_LABELS,
    amount_keyboard,
    catalog_keyboard,
    dish_delete_keyboard,
    dish_keyboard,
    dishes_keyboard,
    DISHES_PAGE,
    skip_keyboard,
    PRODUCT_FIELDS,
    meal_categories,
    meal_detail_keyboard,
    my_product_brand_clear_keyboard,
    my_product_delete_keyboard,
    product_brand_keyboard,
    my_product_edit_cancel_keyboard,
    my_product_keyboard,
    meal_name,
    meal_time_keyboard,
    normalize_meal_category,
    today_keyboard,
    my_product_cancel_keyboard,
    nutrition_menu,
    product_results,
    review_keyboard,
)
from backend.app.services.nutrition.barcode import looks_like_barcode
from telegram_bot.keyboards.nutrition import barcode_result_keyboard, barcode_scan_keyboard
from telegram_bot.security import barcode_throttle
from telegram_bot.services.api import NosiFitAPIError
from telegram_bot.services.barcode_reader import (
    ALLOWED_MIME_TYPES,
    MAX_IMAGE_BYTES,
    BarcodeImageError,
    decode_barcode,
)
from telegram_bot.states.nutrition import NutritionStates


router = Router()
CATALOG_LIMIT = 8
MY_PRODUCTS_LIMIT = 30
SEARCH_LIMIT = 8

# Same limits as the backend, so users get a clear message right away.
MAX_AMOUNT = {"g": 5000.0, "ml": 5000.0, "pcs": 100.0}
PRODUCT_LIMITS = {
    "new_product_kcal": 950.0,
    "new_product_protein": 100.0,
    "new_product_fat": 100.0,
    "new_product_carbs": 100.0,
}
# Values a user may not know: "-" stores them as unknown (NULL).
OPTIONAL_PRODUCT_FIELDS = {"sugar_per_100g", "fiber_per_100g"}
TIME_PATTERN = re.compile(r"(?:[01]?\d|2[0-3])[:.][0-5]\d")


def _api(user_id: int):
    from telegram_bot.runtime import get_api
    return get_api(user_id)


def _format_number(value: float) -> str:
    return f"{value:.1f}".rstrip("0").rstrip(".")


def _parse_number(text: str) -> float | None:
    match = re.search(r"\d+(?:[.,]\d+)?", text or "")
    if not match:
        return None
    return float(match.group().replace(",", "."))


def _parse_amount(text: str) -> float | None:
    value = _parse_number(text)
    return value if value is not None and value > 0 else None


def _amount_error(unit: str) -> str:
    limit = MAX_AMOUNT.get(unit, 5000.0)
    example = "1 або 2" if unit == "pcs" else "150 або 1,5"
    return (
        "Введіть число більше 0 і не більше "
        f"{_format_number(limit)} {UNIT_LABELS.get(unit, unit)}, наприклад {example}."
    )


def _normalize_time(text: str) -> str | None:
    value = (text or "").strip()
    if not TIME_PATTERN.fullmatch(value):
        return None
    hours, minutes = re.split(r"[:.]", value)
    return f"{int(hours):02d}:{minutes}"


def _nutrient_text(value, complete: bool = True) -> str:
    """Fiber or sugar: "—" when unknown, "≥ x г" when only partly known.

    Unknown is never shown as 0 g.
    """
    if value is None:
        return "—"
    text = f"{_format_number(float(value))} г"
    return text if complete else f"≥ {text}"


def _format_day(day: dict) -> str:
    progress = day.get("progress", {})
    goals = day.get("goals", {})
    lines = [
        "🍽 <b>Харчування сьогодні</b>",
        "",
        f"🔥 {progress.get('calories', 0):.0f} / {goals.get('calories', 0):.0f} ккал",
        f"🥩 {progress.get('protein', 0):.1f} / {goals.get('protein', 0):.1f} г білка",
        f"🥑 {progress.get('fat', 0):.1f} / {goals.get('fat', 0):.1f} г жирів",
        f"🍞 {progress.get('carbs', 0):.1f} / {goals.get('carbs', 0):.1f} г вуглеводів",
        f"🌾 Клітковина: {_nutrient_text(progress.get('fiber'), progress.get('fiber_complete', True))}"
        f" · 🍬 Цукор: {_nutrient_text(progress.get('sugar'), progress.get('sugar_complete', True))}",
        "",
        f"<b>Прийоми їжі: {len(day.get('meals', []))}</b>",
    ]
    for meal in day.get("meals", []):
        label = html.escape(meal_name(meal.get("category") or meal.get("name")))
        time = meal.get("time")
        if time:
            label += f" · {html.escape(time)}"
        lines.append(f"\n<b>{label}</b>")
        items = meal.get("items", [])
        if not items:
            lines.append("• Продуктів ще немає")
            continue
        for item in items:
            unit = UNIT_LABELS.get(item.get("unit", "g"), item.get("unit", "g"))
            amount = item.get("amount") or item.get("weight") or 0
            lines.append(
                f"• {html.escape(item.get('name', 'Продукт'))} — "
                f"{_format_number(float(amount))} {unit}"
            )
    return "\n".join(lines)


def _meal_by_category(day: dict, category: str) -> dict | None:
    wanted = normalize_meal_category(category)
    return next(
        (
            meal
            for meal in day.get("meals", [])
            if normalize_meal_category(meal.get("category") or meal.get("name")) == wanted
        ),
        None,
    )


def _format_product(product: dict) -> str:
    unit = UNIT_LABELS.get(product.get("default_unit", "g"), product.get("default_unit", "g"))
    brand = product.get("brand")
    brand_text = f" · {html.escape(brand)}" if brand else ""
    return (
        f"🍽 <b>{html.escape(product.get('name', 'Продукт'))}</b>{brand_text}\n\n"
        f"🔥 {product.get('kcal_per_100g', 0):.0f} ккал / 100 г\n"
        f"🥩 {product.get('protein_per_100g', 0):.1f} г білка · "
        f"🥑 {product.get('fat_per_100g', 0):.1f} г жирів\n"
        f"🍞 {product.get('carbs_per_100g', 0):.1f} г вуглеводів\n"
        f"🍬 Цукор: {_nutrient_text(product.get('sugar_per_100g'))} · "
        f"🌾 Клітковина: {_nutrient_text(product.get('fiber_per_100g'))}\n\n"
        f"Одиниця за замовчуванням: <b>{unit}</b>"
    )


def _format_catalog(mode: str, products: list[dict], query: str = "") -> str:
    title = CATALOG_LABELS.get(mode, "🔎 Пошук")
    suffix = f' для «{html.escape(query)}»' if query else ""
    if mode == "mine" and not products:
        return (
            f"🍽 <b>{title}</b>\n\n"
            "Своїх продуктів поки немає. Створити їх можна під час додавання їжі: "
            "«➕ Додати свій продукт»."
        )
    if mode == "mine":
        return (
            f"🍽 <b>{title}</b>\n\n"
            "Натисніть на продукт, щоб додати його.\n"
            "✏️ — змінити назву чи КБЖВ або видалити. ☆ / ★ — обране."
        )
    if not products:
        return (
            f"🍽 <b>{title}</b>{suffix}\n\n"
            "Тут поки порожньо."
        )
    return (
        f"🍽 <b>{title}</b>{suffix}\n\n"
        "Оберіть продукт. ☆ / ★ — обране."
    )


def _pending_totals(pending: list[dict]) -> dict:
    """Draft totals, computed locally (no request). Fiber and sugar keep
    "unknown" apart from 0: ``None`` when no item knows them, and a
    ``*_complete`` flag when only some do."""
    totals = {"calories": 0.0, "protein": 0.0, "fat": 0.0, "carbs": 0.0}
    partial = {"fiber": [], "sugar": []}
    for item in pending:
        amount = float(item["amount"])
        unit = item["unit"]
        grams_per_unit = float(item.get("grams_per_unit") or 1)
        grams = amount if unit == "g" else amount * grams_per_unit
        factor = grams / 100.0
        totals["calories"] += float(item.get("kcal_per_100g") or 0) * factor
        totals["protein"] += float(item.get("protein_per_100g") or 0) * factor
        totals["fat"] += float(item.get("fat_per_100g") or 0) * factor
        totals["carbs"] += float(item.get("carbs_per_100g") or 0) * factor
        for name in partial:
            value = item.get(f"{name}_per_100g")
            partial[name].append(None if value is None else float(value) * factor)
    for name, values in partial.items():
        known = [value for value in values if value is not None]
        totals[name] = sum(known) if known or not values else None
        totals[f"{name}_complete"] = len(known) == len(values)
    return totals


def _pending_item(source: dict, amount: float, unit: str) -> dict:
    """A draft line from a product or a dish component (per-100 g values)."""
    return {
        "product_id": source.get("product_id", source.get("id")),
        "name": source.get("name", "Продукт"),
        "amount": amount,
        "unit": unit,
        "kcal_per_100g": source.get("kcal_per_100g", 0),
        "protein_per_100g": source.get("protein_per_100g", 0),
        "fat_per_100g": source.get("fat_per_100g", 0),
        "carbs_per_100g": source.get("carbs_per_100g", 0),
        "fiber_per_100g": source.get("fiber_per_100g"),
        "sugar_per_100g": source.get("sugar_per_100g"),
        "grams_per_unit": source.get("grams_per_unit", 1),
    }


def _format_pending(
    category: str,
    pending: list[dict],
    existing: list[dict] | None = None,
    dish_name: str | None = None,
) -> str:
    lines = [f"🍽 <b>{html.escape(meal_name(category))}</b>"]
    if dish_name:
        lines.append(
            f"🍲 Страва «{html.escape(dish_name)}» — зміни стосуються лише цього прийому."
        )
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
        lines.extend(["", "Ви додаєте:"])
        for index, item in enumerate(pending, start=1):
            unit = UNIT_LABELS.get(item["unit"], item["unit"])
            lines.append(
                f"{index}. {html.escape(item['name'])} — "
                f"{_format_number(item['amount'])} {unit}"
            )
        totals = _pending_totals(pending)
        lines.extend([
            "",
            "<b>Разом</b>",
            f"🔥 {totals['calories']:.0f} ккал",
            f"🥩 {totals['protein']:.1f} г білка · 🥑 {totals['fat']:.1f} г жирів",
            f"🍞 {totals['carbs']:.1f} г вуглеводів",
            f"🌾 Клітковина: {_nutrient_text(totals['fiber'], totals['fiber_complete'])}"
            f" · 🍬 Цукор: {_nutrient_text(totals['sugar'], totals['sugar_complete'])}",
        ])
    return "\n".join(lines)


async def _load_catalog(
    user_id: int,
    state: FSMContext,
    mode: str,
) -> list[dict]:
    api = _api(user_id)
    loaders = {
        "favorites": api.get_favorite_products,
        "recent": api.get_recent_products,
        "mine": api.get_my_products,
    }
    limit = MY_PRODUCTS_LIMIT if mode == "mine" else CATALOG_LIMIT
    products = await asyncio.to_thread(loaders[mode], "uk", limit)
    await state.update_data(
        catalog_products=products,
        catalog_mode=mode,
        search_query="",
        search_category="",
        search_offset=0,
    )
    return products


async def _show_catalog(
    callback: CallbackQuery,
    state: FSMContext,
    mode: str,
) -> None:
    try:
        products = await _load_catalog(callback.from_user.id, state, mode)
    except NosiFitAPIError as exc:
        await callback.message.answer(f"Не вдалося завантажити каталог: {exc}")
        return

    await state.set_state(NutritionStates.browsing_catalog)
    await _safe_edit(
        callback.message,
        _format_catalog(mode, products),
        reply_markup=product_results(products, mode=mode),
    )


async def _show_today(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        day = await asyncio.to_thread(_api(callback.from_user.id).get_day)
    except NosiFitAPIError as exc:
        await callback.message.answer(f"Не вдалося завантажити дані: {exc}")
        return
    await state.clear()
    await _safe_edit(
        callback.message,
        _format_day(day),
        reply_markup=today_keyboard(day.get("meals", [])),
    )


async def _show_meal(callback: CallbackQuery, state: FSMContext, meal_id: int) -> None:
    try:
        day = await asyncio.to_thread(_api(callback.from_user.id).get_day)
    except NosiFitAPIError as exc:
        await callback.message.answer(f"Не вдалося завантажити дані: {exc}")
        return
    meal = next((item for item in day.get("meals", []) if int(item.get("id", 0)) == meal_id), None)
    if meal is None:
        await callback.message.answer("Прийом їжі не знайдено.")
        return
    category = html.escape(meal_name(meal.get("category") or meal.get("name")))
    time = meal.get("time")
    title = f"🍽 <b>{category}</b>" + (f" · {html.escape(time)}" if time else "")
    lines = [title, ""]
    items = meal.get("items", [])
    if not items:
        lines.append("Продуктів ще немає.")
    else:
        for item in items:
            unit = UNIT_LABELS.get(item.get("unit", "g"), item.get("unit", "g"))
            amount = item.get("amount") or item.get("weight") or 0
            lines.append(
                f"• {html.escape(item.get('name', 'Продукт'))} — "
                f"{_format_number(float(amount))} {unit}"
            )
    await state.update_data(category=meal.get("category"), meal_id=meal_id)
    await _safe_edit(
        callback.message,
        "\n".join(lines),
        reply_markup=meal_detail_keyboard(meal),
    )


async def _show_product_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(NutritionStates.browsing_catalog)
    await state.update_data(
        catalog_mode="search",
        search_query="",
        search_category="",
        search_offset=0,
    )
    await _safe_edit(
        callback.message,
        "🍽 <b>Додати продукт</b>\n\n"
        "🔎 Напишіть назву або її частину — помилки в написанні не страшні.\n\n"
        "Або відкрийте обрані, нещодавні чи свої продукти.",
        reply_markup=catalog_keyboard(),
    )


async def _start_product_search(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(NutritionStates.searching_product)
    data = await state.get_data()
    await _safe_edit(
        callback.message,
        "🔎 <b>Пошук продукту</b>\n\n"
        "Напишіть назву продукту або її частину.",
        reply_markup=catalog_keyboard(),
    )


async def _perform_product_search(
    message: Message,
    state: FSMContext,
    query: str,
    *,
    offset: int = 0,
) -> None:
    data = await state.get_data()
    try:
        matches, has_more = await asyncio.to_thread(
            _api(message.from_user.id).search_products_page,
            query,
            "uk",
            SEARCH_LIMIT,
            None,
            offset,
        )
    except NosiFitAPIError as exc:
        await message.answer(f"Не вдалося виконати пошук: {exc}")
        return

    current = list(data.get("search_products", []))
    if offset:
        current.extend(matches)
    else:
        current = matches

    await state.update_data(
        search_products=current,
        search_query=query,
        search_offset=offset,
        catalog_mode="search",
    )
    await state.set_state(NutritionStates.searching_product)

    if not matches:
        if offset:
            await message.answer("Це вже всі результати.")
        else:
            await message.answer(
                f"🔎 <b>{html.escape(query)}</b>\n\n"
                "Нічого не знайдено. Спробуйте коротшу назву.",
                reply_markup=catalog_keyboard(),
            )
        return

    names = [(product.get("name") or "").casefold() for product in matches]
    brands = [(product.get("brand") or "").casefold() for product in matches]
    is_fallback = not any(query.casefold() in value for value in names + brands)
    prefix = (
        "🔎 <b>Можливо, ви шукали:</b>\n\n"
        if is_fallback and offset == 0
        else ""
    )
    await message.answer(
        prefix + _format_catalog("search", current, query),
        reply_markup=product_results(
            current,
            mode="search",
            query=query,
            category=None,
            offset=offset,
            has_more=has_more,
        ),
    )


async def _show_review(message: Message, state: FSMContext, *, edit: bool = False) -> None:
    data = await state.get_data()
    pending = data.get("pending", [])
    await state.set_state(NutritionStates.reviewing)
    if data.get("building_dish"):
        text = _format_new_dish(data.get("dish_builder_name") or "", pending)
        keyboard = review_keyboard(pending, building_dish=True)
    else:
        dish_name = data.get("draft_dish_name")
        text = _format_pending(
            data.get("category"), pending, data.get("existing_items", []), dish_name
        )
        keyboard = review_keyboard(pending, dish_name)
    if edit:
        await _safe_edit(message, text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)


async def _safe_edit(message: Message, text: str, *, reply_markup=None) -> None:
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc).lower():
            raise



# ---------- Barcode: photo or typed digits ----------
#
# The photo is downloaded into memory, decoded locally and dropped; only the
# digits go to NosiFit, which looks them up with the same service as the
# website (catalog → cache → Open Food Facts). Registered before the state
# handlers below so a photo is never read as an amount or a name.

BARCODE_SCAN_TEXT = (
    "📷 <b>Штрихкод</b>\n\n"
    "Надішліть фото штрихкоду продукту — так, щоб він був чітким і займав "
    "більшу частину кадру. Або напишіть цифри під штрихкодом."
)
BARCODE_RETRY_TEXT = (
    "Не вдалося розпізнати штрихкод. Надішліть чіткіше фото: штрихкод "
    "ближче, рівно, без відблисків і розмиття. Або напишіть цифри під ним."
)
BARCODE_WARNINGS = {
    "per_100ml": "Значення на 100 мл. У мілілітрах облік точний; у грамах вважається 1 г = 1 мл.",
    "converted_from_serving": "Частину значень перераховано з порції на 100 г за вагою порції з етикетки.",
    "energy_from_kj": "Калорії перераховано з кДж.",
    "salt_from_sodium": "Сіль розраховано з натрію (× 2,5).",
    "energy_mismatch": "Калорії помітно не збігаються з БЖВ — звірте з етикеткою.",
    "no_nutrition_data": "У базі позначено, що на упаковці немає харчової цінності.",
    "basis_uncertain": "Невідомо, чи значення на 100 г чи на 100 мл — звірте з етикеткою.",
}
BARCODE_FIELDS = {
    "name": "назва",
    "kcal_per_100g": "калорії",
    "protein_per_100g": "білки",
    "fat_per_100g": "жири",
    "carbs_per_100g": "вуглеводи",
    "fiber_per_100g": "клітковина",
    "sugar_per_100g": "цукор",
    "saturated_fat_per_100g": "насичені жири",
    "salt_per_100g": "сіль",
}


async def _download_file(bot, file_id: str) -> bytes:
    """The file's bytes, in memory only (never written to disk)."""
    buffer = io.BytesIO()
    try:
        await bot.download(file_id, destination=buffer, timeout=20)
        return buffer.getvalue()
    finally:
        buffer.close()


def _barcode_file(message: Message) -> tuple[str, int | None] | None:
    """(file_id, size) of the image in the message, or None."""
    if message.photo:
        # Largest size that is still within the limit (Telegram sends several).
        sizes = [p for p in message.photo if (p.file_size or 0) <= MAX_IMAGE_BYTES]
        best = max(sizes or message.photo, key=lambda p: p.width * p.height)
        return best.file_id, best.file_size
    document = message.document
    if document and (document.mime_type or "").lower() in ALLOWED_MIME_TYPES:
        return document.file_id, document.file_size
    return None


def _value_text(value, unit: str = "г") -> str:
    return "—" if value is None else f"{_format_number(float(value))} {unit}"


def _format_barcode_preview(result: dict) -> str:
    preview = result["preview"]
    basis = "100 мл" if preview.get("basis") == "100ml" else "100 г"
    name = preview.get("name") or "Без назви"
    brand = preview.get("brand")
    lines = [
        f"📷 <b>{html.escape(name)}</b>" + (f" · {html.escape(brand)}" if brand else ""),
        f"Штрихкод: <code>{html.escape(result['barcode'])}</code>",
        "Джерело: Open Food Facts — дані спільноти, <b>не перевірені</b> NosiFit.",
        "",
        f"<b>На {basis}</b>",
        f"🔥 {_value_text(preview.get('kcal_per_100g'), 'ккал')}",
        f"🥩 Білки: {_value_text(preview.get('protein_per_100g'))} · "
        f"🥑 Жири: {_value_text(preview.get('fat_per_100g'))}",
        f"🍞 Вуглеводи: {_value_text(preview.get('carbs_per_100g'))} · "
        f"🍬 Цукор: {_value_text(preview.get('sugar_per_100g'))}",
        f"🌾 Клітковина: {_value_text(preview.get('fiber_per_100g'))} · "
        f"Насичені жири: {_value_text(preview.get('saturated_fat_per_100g'))} · "
        f"Сіль: {_value_text(preview.get('salt_per_100g'))}",
    ]
    notes = [BARCODE_WARNINGS[w] for w in preview.get("warnings", []) if w in BARCODE_WARNINGS]
    if result.get("stale"):
        notes.append("Open Food Facts зараз недоступний — показано збережені раніше дані.")
    if notes:
        lines.append("")
        lines.extend(f"⚠️ {note}" for note in notes)
    if preview.get("missing"):
        lines.append("")
        lines.append(
            "❗ Бракує: " + ", ".join(BARCODE_FIELDS.get(f, f) for f in preview["missing"]) + "."
        )
    if preview.get("invalid"):
        lines.append(
            "❗ Неправдоподібні значення: "
            + ", ".join(BARCODE_FIELDS.get(f, f) for f in preview["invalid"]) + "."
        )
    lines.append("")
    if preview.get("importable"):
        lines.append("Перевірте значення з етикеткою й додайте продукт.")
    else:
        lines.append("Цих даних недостатньо для обліку. Створіть свій продукт з етикетки.")
    lines.append("<i>Дані: Open Food Facts, ліцензія ODbL.</i>")
    return "\n".join(lines)


async def _barcode_lookup(message: Message, state: FSMContext, code: str) -> None:
    try:
        result = await asyncio.to_thread(_api(message.from_user.id).lookup_barcode, code)
    except NosiFitAPIError as exc:
        await state.set_state(NutritionStates.scanning_barcode)
        await message.answer(str(exc), reply_markup=barcode_scan_keyboard())
        return

    barcode = result.get("barcode") or code
    await state.update_data(barcode_code=barcode)

    if result.get("status") == "found" and result.get("product"):
        text, keyboard = await _select_product(
            state,
            result["product"],
            prefix=f"📷 Штрихкод <code>{html.escape(barcode)}</code>\n",
        )
        await message.answer(text, reply_markup=keyboard)
        return

    await state.set_state(NutritionStates.scanning_barcode)
    if result.get("status") == "found" and result.get("preview"):
        await state.update_data(barcode_preview=result["preview"])
        await message.answer(
            _format_barcode_preview(result),
            reply_markup=barcode_result_keyboard(barcode, bool(result["preview"].get("importable"))),
        )
        return

    await state.update_data(barcode_preview=None)
    await message.answer(
        f"📷 Штрихкод <code>{html.escape(barcode)}</code>\n\n"
        "Такого продукту немає ні в каталозі NosiFit, ні в Open Food Facts. "
        "Створіть свій продукт з етикетки — наступного разу він знайдеться за цим штрихкодом.",
        reply_markup=barcode_result_keyboard(barcode, False),
    )


@router.callback_query(F.data == "nutrition:barcode")
async def barcode_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(NutritionStates.scanning_barcode)
    await _safe_edit(callback.message, BARCODE_SCAN_TEXT, reply_markup=barcode_scan_keyboard())


@router.message(F.photo | F.document)
async def barcode_photo(message: Message, state: FSMContext) -> None:
    found = _barcode_file(message)
    if found is None:
        await message.answer("Надішліть фото (JPEG, PNG або WebP) зі штрихкодом.")
        return
    try:
        _api(message.from_user.id)  # sign-in first: no download for strangers
    except NosiFitAPIError as exc:
        await message.answer(str(exc))
        return
    if not barcode_throttle.allow(message.from_user.id):
        await message.answer("Забагато фото поспіль. Спробуйте за хвилину.")
        return

    file_id, size = found
    if size is not None and size > MAX_IMAGE_BYTES:
        await message.answer("Файл завеликий. Надішліть звичайне фото штрихкоду (до 10 МБ).")
        return

    await state.set_state(NutritionStates.scanning_barcode)
    try:
        data = await _download_file(message.bot, file_id)
    except Exception:
        await message.answer(
            "Не вдалося отримати фото. Спробуйте ще раз або напишіть цифри під штрихкодом.",
            reply_markup=barcode_scan_keyboard(),
        )
        return
    try:
        code = await asyncio.to_thread(decode_barcode, data)
    except BarcodeImageError:
        code = None
    finally:
        del data

    if code is None:
        await message.answer(BARCODE_RETRY_TEXT, reply_markup=barcode_scan_keyboard())
        return
    await _barcode_lookup(message, state, code)


@router.callback_query(F.data.startswith("nutrition:bc_import:"))
async def barcode_import(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    code = callback.data.rsplit(":", 1)[1]
    try:
        product = await asyncio.to_thread(_api(callback.from_user.id).import_barcode, code)
    except NosiFitAPIError as exc:
        await callback.message.answer(str(exc), reply_markup=barcode_result_keyboard(code, False))
        return
    text, keyboard = await _select_product(
        state, product, prefix="✅ Продукт додано до каталогу NosiFit.\n\n"
    )
    await _safe_edit(callback.message, text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("nutrition:bc_own:"))
async def barcode_own_product(callback: CallbackQuery, state: FSMContext) -> None:
    """Own product typed from the label; it keeps the scanned barcode."""
    await callback.answer()
    code = callback.data.rsplit(":", 1)[1]
    if not looks_like_barcode(code):
        return
    data = await state.get_data()
    preview = data.get("barcode_preview") or {}
    hint = ""
    if preview.get("name"):
        hint = f"\nНазва в Open Food Facts: <b>{html.escape(preview['name'])}</b>"
    await state.update_data(new_product_barcode=code)
    await state.set_state(NutritionStates.product_name)
    await _safe_edit(
        callback.message,
        "➕ <b>Мій продукт</b> зі штрихкодом "
        f"<code>{html.escape(code)}</code>{hint}\n\n"
        "Введіть назву продукту, далі — значення з етикетки на 100 г.",
        reply_markup=my_product_cancel_keyboard(),
    )


@router.message(F.text.in_({NUTRITION, FOOD}))
async def nutrition(message: Message, state: FSMContext) -> None:
    await state.clear()
    if message.text == NUTRITION:
        # Entering the mode: its own buttons (food, water, weight, home).
        await message.answer("🍽 Харчування", reply_markup=nutrition_mode_menu())
    try:
        day = await asyncio.to_thread(_api(message.from_user.id).get_day)
    except NosiFitAPIError as exc:
        await message.answer(
            f"Не вдалося підключитися до NosiFit: {exc}",
            reply_markup=nutrition_mode_menu(),
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
    category = normalize_meal_category(callback.data.split(":", 2)[2])
    if category is None:
        return
    try:
        day = await asyncio.to_thread(_api(callback.from_user.id).get_day)
    except NosiFitAPIError as exc:
        await callback.message.answer(f"Не вдалося завантажити дані: {exc}")
        return

    meal = _meal_by_category(day, category)
    data = await state.get_data()
    pending = list(data.get("pending", []))
    await state.update_data(
        category=category,
        meal_id=meal.get("id", 0) if meal else 0,
        meal_time=meal.get("time") if meal else None,
        existing_items=meal.get("items", []) if meal else [],
        pending=pending,
        catalog_products=[],
        search_products=[],
        catalog_mode="search",
        search_query="",
        search_category="",
        search_offset=0,
    )
    if meal:
        if pending:
            await _show_review(callback.message, state, edit=True)
        else:
            await _show_product_menu(callback, state)
        return
    await state.set_state(NutritionStates.entering_meal_time)
    await _safe_edit(
        callback.message,
        f"🍽 <b>{html.escape(meal_name(category))}</b>\n\n"
        "О котрій ви їли? Напишіть час, наприклад <b>13:30</b>, "
        "або виберіть нижче.",
        reply_markup=meal_time_keyboard(),
    )


@router.callback_query(
    F.data.startswith("nutrition:catalog:"),
)
async def switch_catalog(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    mode = callback.data.rsplit(":", 1)[1]
    if mode not in CATALOG_LABELS:
        return
    await _show_catalog(callback, state, mode)


@router.callback_query(F.data == "nutrition:product_menu")
async def product_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _show_product_menu(callback, state)


@router.callback_query(
    NutritionStates.entering_meal_time,
    F.data.startswith("nutrition:meal_time:"),
)
async def choose_meal_time(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    value = callback.data.rsplit(":", 1)[1]
    from telegram_bot.runtime import local_now

    meal_time = local_now().strftime("%H:%M") if value == "now" else None
    await state.update_data(meal_time=meal_time)
    if (await state.get_data()).get("pending"):
        await _show_review(callback.message, state, edit=True)
        return
    await state.set_state(NutritionStates.browsing_catalog)
    await callback.message.edit_text(
        "🍽 <b>Додати продукт</b>\n\n"
        "🔎 Напишіть назву або відкрийте обрані, нещодавні чи свої продукти.",
        reply_markup=catalog_keyboard(),
    )


@router.message(NutritionStates.entering_meal_time)
async def enter_meal_time(message: Message, state: FSMContext) -> None:
    value = _normalize_time(message.text or "")
    if value is None:
        await message.answer(
            "Напишіть час як <b>08:30</b> "
            "або натисніть «Поточний час».",
            reply_markup=meal_time_keyboard(),
        )
        return
    await state.update_data(meal_time=value)
    if (await state.get_data()).get("pending"):
        await _show_review(message, state)
        return
    await state.set_state(NutritionStates.browsing_catalog)
    await message.answer(
        "🍽 <b>Додати продукт</b>\n\n"
        "🔎 Напишіть назву або відкрийте обрані, нещодавні чи свої продукти.",
        reply_markup=catalog_keyboard(),
    )


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
        await message.answer("Напишіть назву продукту або її частину.")
        return
    if looks_like_barcode(query):
        # Digits under a barcode, typed in: the same lookup as a scan.
        await _barcode_lookup(message, state, query)
        return
    await _perform_product_search(message, state, query, offset=0)


@router.callback_query(F.data.startswith("nutrition:more_results:"))
async def more_product_results(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    offset = int(callback.data.rsplit(":", 1)[1])
    data = await state.get_data()
    query = data.get("search_query", "")
    if not query:
        await _start_product_search(callback, state)
        return

    try:
        matches, has_more = await asyncio.to_thread(
            _api(callback.from_user.id).search_products_page,
            query,
            "uk",
            SEARCH_LIMIT,
            data.get("search_category") or None,
            offset,
        )
    except NosiFitAPIError as exc:
        await callback.message.answer(f"Не вдалося завантажити ще результати: {exc}")
        return

    current = list(data.get("search_products", []))
    current.extend(matches)
    await state.update_data(search_products=current, search_offset=offset)
    await _safe_edit(
        callback.message,
        _format_catalog("search", current, query),
        reply_markup=product_results(
            current,
            mode="search",
            query=query,
            category=None,
            offset=offset,
            has_more=has_more,
        ),
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
        mode = data.get("catalog_mode", "search")
        if mode in CATALOG_LABELS:
            await _show_catalog(callback, state, mode)
        else:
            query = data.get("search_query", "")
            products = data.get("search_products", [])
            await _safe_edit(
                callback.message,
                _format_catalog("search", products, query),
                reply_markup=product_results(
                    products,
                    mode="search",
                    query=query,
                    category=None,
                    offset=data.get("search_offset", 0),
                    has_more=False,
                ),
            )
    except NosiFitAPIError as exc:
        await callback.message.answer(f"Не вдалося змінити обране: {exc}")


@router.callback_query(
    F.data.startswith("nutrition:product:"),
)
async def choose_product(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    product_id = int(callback.data.rsplit(":", 1)[1])
    data = await state.get_data()
    product_lists = [
        data.get("catalog_products", []),
        data.get("search_products", []),
    ]
    product = next(
        (
            product
            for products in product_lists
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

    text, keyboard = await _select_product(state, product)
    await callback.message.edit_text(text, reply_markup=keyboard)


async def _select_product(state: FSMContext, product: dict, prefix: str = ""):
    """Makes ``product`` the one being added; returns the amount prompt."""
    product_id = int(product["id"])
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
        product_fiber_per_100g=product.get("fiber_per_100g"),
        product_sugar_per_100g=product.get("sugar_per_100g"),
        product_grams_per_unit=product.get("grams_per_unit", 1),
    )
    await state.set_state(NutritionStates.entering_amount)
    text = (
        prefix
        + _format_product(product)
        + "\n\n"
        f"Введіть кількість у <b>{UNIT_LABELS.get(unit, unit)}</b>. "
        f"За замовчуванням: <b>{default_amount:g}</b>."
    )
    return text, amount_keyboard(unit, product_id if product.get("is_own") else None)


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
    data = await state.get_data()
    unit = data.get("product_unit", "g")
    amount = _parse_amount(message.text or "")
    if amount is None or amount > MAX_AMOUNT.get(unit, 5000.0):
        await message.answer(_amount_error(unit))
        return

    pending = list(data.get("pending", []))
    item = _pending_item(
        {
            "product_id": data["product_id"],
            "name": data["product_name"],
            "kcal_per_100g": data.get("product_kcal_per_100g", 0),
            "protein_per_100g": data.get("product_protein_per_100g", 0),
            "fat_per_100g": data.get("product_fat_per_100g", 0),
            "carbs_per_100g": data.get("product_carbs_per_100g", 0),
            "fiber_per_100g": data.get("product_fiber_per_100g"),
            "sugar_per_100g": data.get("product_sugar_per_100g"),
            "grams_per_unit": data.get("product_grams_per_unit", 1),
        },
        amount,
        data["product_unit"],
    )
    editing_index = data.get("editing_index")
    if editing_index is not None and 0 <= int(editing_index) < len(pending):
        pending[int(editing_index)] = item
    else:
        pending.append(item)
    await state.update_data(pending=pending, editing_index=None)

    if data.get("building_dish"):
        await _show_review(message, state)
        return

    # The product was picked without a meal (old buttons after a bot restart
    # wipe the in-memory state): keep the draft and ask for the meal first.
    if not data.get("category") and not data.get("meal_id"):
        await state.set_state(NutritionStates.choosing_meal)
        await message.answer(
            f"Додано: <b>{html.escape(item['name'])}</b>.\n\n"
            "До якого прийому їжі його записати?",
            reply_markup=meal_categories(),
        )
        return

    await _show_review(message, state)


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
        product_fiber_per_100g=item.get("fiber_per_100g"),
        product_sugar_per_100g=item.get("sugar_per_100g"),
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
    if not pending and not data.get("building_dish"):
        await _safe_edit(
            callback.message,
            f"🍽 <b>{html.escape(meal_name(data.get('category')))}</b>\n\n"
            "Поки нічого не додано. Додайте продукт або скасуйте.",
            reply_markup=review_keyboard(pending),
        )
        return
    await _show_review(callback.message, state, edit=True)


@router.callback_query(NutritionStates.reviewing, F.data == "nutrition:more")
async def add_more(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(NutritionStates.searching_product)
    await _start_product_search(callback, state)


@router.callback_query(NutritionStates.reviewing, F.data == "nutrition:save")
async def save_meal(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = await state.get_data()
    await state.set_state(NutritionStates.saving)
    pending = data.get("pending", [])
    category = data.get("category")

    if not pending:
        await state.set_state(NutritionStates.reviewing)
        await callback.message.answer("У прийомі ще немає нових продуктів.")
        return

    if not category and not data.get("meal_id"):
        await state.set_state(NutritionStates.choosing_meal)
        await callback.message.answer(
            "До якого прийому їжі записати продукти?",
            reply_markup=meal_categories(),
        )
        return

    items = [
        {"product_id": item["product_id"], "amount": item["amount"], "unit": item["unit"]}
        for item in pending
    ]
    try:
        api = _api(callback.from_user.id)
        if category:
            # One request: the server finds or creates the meal, stores the
            # snapshot entries (tagged with the dish they came from) and
            # returns the updated day.
            result = await asyncio.to_thread(
                api.log_food,
                category,
                items,
                dish_id=data.get("draft_dish_id"),
                time=data.get("meal_time"),
            )
            updated_day = result["day"]
        else:
            # A meal opened from "today" without a known category.
            await asyncio.to_thread(api.add_entries, int(data.get("meal_id") or 0), items)
            updated_day = await asyncio.to_thread(api.get_day)
    except NosiFitAPIError as exc:
        await state.set_state(NutritionStates.reviewing)
        await callback.message.answer(
            f"Не вдалося зберегти прийом: {exc}\n\n"
            "Вибрані продукти не втрачено — спробуйте ще раз."
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
    await _show_today(callback, state)


@router.callback_query(F.data == "nutrition:back")
async def back_to_nutrition(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    try:
        day = await asyncio.to_thread(_api(callback.from_user.id).get_day)
    except NosiFitAPIError as exc:
        await callback.message.answer(f"Не вдалося завантажити дані: {exc}")
        return
    await _safe_edit(callback.message, _format_day(day), reply_markup=nutrition_menu())


@router.callback_query(F.data.startswith("nutrition:meal_view:"))
async def meal_view(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _show_meal(callback, state, int(callback.data.rsplit(":", 1)[1]))


@router.callback_query(F.data.startswith("nutrition:meal_add:"))
async def meal_add(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    meal_id = int(callback.data.rsplit(":", 1)[1])
    data = await state.get_data()
    await state.update_data(
        meal_id=meal_id,
        pending=[],
        existing_items=[],
        category=data.get("category"),
        meal_time=data.get("meal_time"),
    )
    await _show_product_menu(callback, state)


@router.callback_query(F.data.startswith("nutrition:entry_edit:"))
async def edit_existing_entry(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    entry_id = int(callback.data.rsplit(":", 1)[1])
    try:
        day = await asyncio.to_thread(_api(callback.from_user.id).get_day)
    except NosiFitAPIError as exc:
        await callback.message.answer(f"Не вдалося завантажити дані: {exc}")
        return
    meal_id, item = next(
        (
            (int(meal.get("id", 0)), item)
            for meal in day.get("meals", [])
            for item in meal.get("items", [])
            if int(item.get("id", 0)) == entry_id
        ),
        (0, None),
    )
    if item is None:
        await callback.message.answer("Продукт не знайдено.")
        return
    unit = item.get("unit") or "g"
    await state.update_data(
        editing_entry_id=entry_id,
        editing_entry_unit=unit,
        editing_entry_meal_id=meal_id,
    )
    await state.set_state(NutritionStates.editing_entry)
    await _safe_edit(
        callback.message,
        f"✏️ <b>{html.escape(item.get('name', 'Продукт'))}</b>\n\n"
        f"Поточна кількість: <b>{_format_number(float(item.get('amount') or item.get('weight') or 0))} "
        f"{UNIT_LABELS.get(unit, unit)}</b>\n"
        "Введіть нову кількість.",
        reply_markup=amount_keyboard(unit),
    )


@router.message(NutritionStates.editing_entry)
async def save_existing_entry_amount(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    unit = data.get("editing_entry_unit", "g")
    amount = _parse_amount(message.text or "")
    if amount is None or amount > MAX_AMOUNT.get(unit, 5000.0):
        await message.answer(_amount_error(unit))
        return
    try:
        await asyncio.to_thread(
            _api(message.from_user.id).update_entry,
            int(data["editing_entry_id"]),
            amount=amount,
            unit=data.get("editing_entry_unit", "g"),
            meal_id=int(data.get("editing_entry_meal_id") or 0),
        )
    except NosiFitAPIError as exc:
        await message.answer(f"Не вдалося оновити продукт: {exc}")
        return
    await state.clear()
    try:
        day = await asyncio.to_thread(_api(message.from_user.id).get_day)
    except NosiFitAPIError:
        await message.answer("✅ Кількість продукту оновлено.")
        return
    await message.answer(
        "✅ Кількість продукту оновлено.\n\n" + _format_day(day),
        reply_markup=today_keyboard(day.get("meals", [])),
    )


@router.callback_query(F.data.startswith("nutrition:entry_delete:"))
async def delete_existing_entry(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    entry_id = int(callback.data.rsplit(":", 1)[1])
    try:
        await asyncio.to_thread(_api(callback.from_user.id).delete_entry, entry_id)
    except NosiFitAPIError as exc:
        if "Entry not found" not in str(exc):
            await callback.message.answer(f"Не вдалося видалити продукт: {exc}")
            return
    await _show_today(callback, state)


@router.callback_query(F.data == "nutrition:my-product")
async def my_product_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.update_data(new_product_barcode=None)
    await state.set_state(NutritionStates.product_name)
    await callback.message.edit_text(
        "➕ <b>Мій продукт</b>\n\n"
        "Введіть назву продукту:",
        reply_markup=my_product_cancel_keyboard(),
    )


@router.message(NutritionStates.product_name)
async def my_product_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name or len(name) > 120:
        await message.answer("Введіть назву продукту (до 120 символів).")
        return
    await state.update_data(new_product_name=name, new_product_brand=None)
    await state.set_state(NutritionStates.product_brand)
    await message.answer(
        "Введіть бренд або виробника (до 120 символів), наприклад <b>Галичина</b>.\n"
        "Якщо бренду немає — натисніть «Без бренду».",
        reply_markup=product_brand_keyboard(),
    )


async def _ask_product_kcal(message: Message, state: FSMContext) -> None:
    await state.set_state(NutritionStates.product_kcal)
    await message.answer("Введіть калорійність на 100 г, наприклад <b>250</b>. Можна 0.")


@router.message(NutritionStates.product_brand)
async def my_product_brand(message: Message, state: FSMContext) -> None:
    brand = (message.text or "").strip()
    if not brand or len(brand) > 120:
        await message.answer(
            "Бренд має бути до 120 символів. Або натисніть «Без бренду».",
            reply_markup=product_brand_keyboard(),
        )
        return
    await state.update_data(new_product_brand=brand)
    await _ask_product_kcal(message, state)


@router.callback_query(NutritionStates.product_brand, F.data == "nutrition:brand_skip")
async def my_product_brand_skip(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.update_data(new_product_brand=None)
    await _ask_product_kcal(callback.message, state)


async def _read_product_number(
    message: Message,
    state: FSMContext,
    next_state: NutritionStates,
    key: str,
    prompt: str,
) -> None:
    value = _parse_number(message.text or "")
    limit = PRODUCT_LIMITS.get(key, 100.0)
    if value is None or value > limit:
        await message.answer(f"Введіть число від 0 до {_format_number(limit)} (на 100 г).")
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
    value = _parse_number(message.text or "")
    if value is None or value > PRODUCT_LIMITS["new_product_carbs"]:
        await message.answer("Введіть число від 0 до 100 (на 100 г).")
        return
    await state.update_data(new_product_carbs=value)
    await state.set_state(NutritionStates.product_sugar)
    await message.answer(
        "Скільки з них цукру на 100 г? Якщо на етикетці немає — пропустіть.",
        reply_markup=skip_keyboard("nutrition:skip_sugar"),
    )


async def _read_optional_number(message: Message, state: FSMContext, key: str, limit: float) -> bool:
    value = _parse_number(message.text or "")
    if value is None or value > limit:
        await message.answer(
            f"Введіть число від 0 до {_format_number(limit)} або натисніть «пропустити».",
            reply_markup=skip_keyboard(
                "nutrition:skip_sugar" if key == "new_product_sugar" else "nutrition:skip_fiber"
            ),
        )
        return False
    await state.update_data(**{key: value})
    return True


async def _ask_product_fiber(message: Message, state: FSMContext) -> None:
    await state.set_state(NutritionStates.product_fiber)
    await message.answer(
        "Клітковина на 100 г? Не знаєте — пропустіть, це не завадить.",
        reply_markup=skip_keyboard("nutrition:skip_fiber"),
    )


@router.message(NutritionStates.product_sugar)
async def my_product_sugar(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    limit = float(data.get("new_product_carbs") or 0)
    if await _read_optional_number(message, state, "new_product_sugar", limit):
        await _ask_product_fiber(message, state)


@router.callback_query(NutritionStates.product_sugar, F.data == "nutrition:skip_sugar")
async def my_product_sugar_skip(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    # Unknown stays unknown (NULL), never 0.
    await state.update_data(new_product_sugar=None)
    await _ask_product_fiber(callback.message, state)


@router.message(NutritionStates.product_fiber)
async def my_product_fiber(message: Message, state: FSMContext) -> None:
    if await _read_optional_number(message, state, "new_product_fiber", 100.0):
        await _create_my_product(message, message.from_user.id, state)


@router.callback_query(NutritionStates.product_fiber, F.data == "nutrition:skip_fiber")
async def my_product_fiber_skip(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.update_data(new_product_fiber=None)
    await _create_my_product(callback.message, callback.from_user.id, state)


async def _create_my_product(message: Message, user_id: int, state: FSMContext) -> None:
    data = await state.get_data()
    value = data["new_product_carbs"]
    payload = {
        "name": data["new_product_name"],
        "brand": data.get("new_product_brand"),
        # Set when the product is typed in after a barcode scan.
        "barcode": data.get("new_product_barcode"),
        "kcal_per_100g": data["new_product_kcal"],
        "protein_per_100g": data["new_product_protein"],
        "fat_per_100g": data["new_product_fat"],
        "carbs_per_100g": value,
        "default_unit": "g",
        "grams_per_unit": 1,
    }
    # Sent only when known: a missing value is stored as unknown, not 0.
    for key, field in (("new_product_sugar", "sugar_per_100g"), ("new_product_fiber", "fiber_per_100g")):
        if data.get(key) is not None:
            payload[field] = data[key]
    try:
        product = await asyncio.to_thread(_api(user_id).create_product, payload)
    except NosiFitAPIError as exc:
        await message.answer(f"Не вдалося створити продукт: {exc}")
        return
    await state.update_data(new_product_barcode=None)

    await state.update_data(
        product_id=product["id"],
        product_name=product["name"],
        product_unit=product.get("default_unit", "g"),
        product_kcal_per_100g=product.get("kcal_per_100g", data["new_product_kcal"]),
        product_protein_per_100g=product.get("protein_per_100g", data["new_product_protein"]),
        product_fat_per_100g=product.get("fat_per_100g", data["new_product_fat"]),
        product_carbs_per_100g=product.get("carbs_per_100g", value),
        product_fiber_per_100g=product.get("fiber_per_100g"),
        product_sugar_per_100g=product.get("sugar_per_100g"),
        product_grams_per_unit=product.get("grams_per_unit", 1),
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
        reply_markup=nutrition_mode_menu(),
    )


# ---------- Editing the user's own products ----------

def _format_my_product(product: dict) -> str:
    unit = UNIT_LABELS.get(product.get("default_unit", "g"), product.get("default_unit", "g"))
    brand = product.get("brand")
    brand_line = f"Бренд: <b>{html.escape(brand)}</b>\n" if brand else "Бренд: —\n"
    return (
        f"✏️ <b>{html.escape(product.get('name', 'Продукт'))}</b>\n\n"
        + brand_line
        + f"Ккал: <b>{_format_number(float(product.get('kcal_per_100g') or 0))}</b> на 100 г\n"
        f"Білки: <b>{_format_number(float(product.get('protein_per_100g') or 0))}</b> г · "
        f"Жири: <b>{_format_number(float(product.get('fat_per_100g') or 0))}</b> г · "
        f"Вуглеводи: <b>{_format_number(float(product.get('carbs_per_100g') or 0))}</b> г\n"
        f"Цукор: <b>{_nutrient_text(product.get('sugar_per_100g'))}</b> · "
        f"Клітковина: <b>{_nutrient_text(product.get('fiber_per_100g'))}</b>\n"
        f"Одиниця: {unit}\n\n"
        "Що змінити? Нові значення діють для нових записів; "
        "уже записані прийоми їжі не зміняться."
    )


async def _send_my_product(message: Message, user_id: int, product_id: int, *, edit: bool, prefix: str = "") -> None:
    try:
        product = await asyncio.to_thread(_api(user_id).get_product, product_id)
    except NosiFitAPIError as exc:
        await message.answer(str(exc))
        return

    if not product.get("is_own"):
        await message.answer("Змінювати можна лише власні продукти.")
        return

    text = prefix + _format_my_product(product)
    if edit:
        await _safe_edit(message, text, reply_markup=my_product_keyboard(product_id))
    else:
        await message.answer(text, reply_markup=my_product_keyboard(product_id))


@router.callback_query(F.data.startswith("nutrition:myprod:"))
async def my_product_card(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    product_id = int(callback.data.rsplit(":", 1)[1])
    if await state.get_state() == NutritionStates.editing_product_field.state:
        await state.set_state(None)
    await _send_my_product(callback.message, callback.from_user.id, product_id, edit=True)


@router.callback_query(F.data.startswith("nutrition:myprod_edit:"))
async def my_product_edit_field(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    _, _, product_id, field = callback.data.split(":", 3)
    if field not in PRODUCT_FIELDS:
        return

    await state.set_state(NutritionStates.editing_product_field)
    await state.update_data(edit_product_id=int(product_id), edit_product_field=field)

    if field == "name":
        prompt = "Введіть нову назву продукту (до 120 символів):"
    elif field == "brand":
        await _safe_edit(
            callback.message,
            "Введіть новий бренд (до 120 символів) або приберіть його:",
            reply_markup=my_product_brand_clear_keyboard(int(product_id)),
        )
        return
    else:
        limit = 950 if field == "kcal_per_100g" else 100
        prompt = (
            f"Введіть нове значення «{PRODUCT_FIELDS[field]}» на 100 г "
            f"(від 0 до {limit}), наприклад <b>12,5</b>:"
        )
        if field in OPTIONAL_PRODUCT_FIELDS:
            prompt += "\nНе знаєте — надішліть «-»."
    await _safe_edit(callback.message, prompt, reply_markup=my_product_edit_cancel_keyboard(int(product_id)))


@router.message(NutritionStates.editing_product_field)
async def my_product_save_field(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    product_id = int(data.get("edit_product_id") or 0)
    field = data.get("edit_product_field")
    if not product_id or field not in PRODUCT_FIELDS:
        await state.set_state(None)
        return

    if field in ("name", "brand"):
        value = (message.text or "").strip()
        if not value or len(value) > 120:
            await message.answer(
                "Текст не може бути порожнім або довшим за 120 символів.",
                reply_markup=my_product_edit_cancel_keyboard(product_id),
            )
            return
    elif field in OPTIONAL_PRODUCT_FIELDS and (message.text or "").strip() in ("-", "—"):
        value = None  # unknown
    else:
        value = _parse_number(message.text or "")
        limit = 950.0 if field == "kcal_per_100g" else 100.0
        if value is None or value > limit:
            await message.answer(
                f"Введіть число від 0 до {_format_number(limit)}.",
                reply_markup=my_product_edit_cancel_keyboard(product_id),
            )
            return

    try:
        await asyncio.to_thread(_api(message.from_user.id).update_product, product_id, {field: value})
    except NosiFitAPIError as exc:
        await message.answer(str(exc), reply_markup=my_product_edit_cancel_keyboard(product_id))
        return

    await state.set_state(None)
    await state.update_data(edit_product_id=None, edit_product_field=None)
    await _send_my_product(message, message.from_user.id, product_id, edit=False, prefix="✅ Збережено.\n\n")


@router.callback_query(F.data.startswith("nutrition:myprod_delete:"))
async def my_product_delete(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    product_id = int(callback.data.rsplit(":", 1)[1])
    await _safe_edit(
        callback.message,
        "Видалити цей продукт?\n\n"
        "Він зникне зі списків, а вже записані прийоми їжі не зміняться.",
        reply_markup=my_product_delete_keyboard(product_id),
    )


@router.callback_query(F.data.startswith("nutrition:myprod_delete_yes:"))
async def my_product_delete_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    product_id = int(callback.data.rsplit(":", 1)[1])
    try:
        await asyncio.to_thread(_api(callback.from_user.id).delete_product, product_id)
    except NosiFitAPIError as exc:
        if getattr(exc, "code", None) != "product_not_found":
            await callback.message.answer(str(exc))
            return

    data = await state.get_data()
    pending = [item for item in data.get("pending", []) if item.get("product_id") != product_id]
    await state.update_data(pending=pending)
    await callback.message.answer("🗑 Продукт видалено.")
    await _show_catalog(callback, state, "mine")


@router.callback_query(F.data.startswith("nutrition:myprod_brand_clear:"))
async def my_product_brand_clear(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    product_id = int(callback.data.rsplit(":", 1)[1])
    try:
        await asyncio.to_thread(_api(callback.from_user.id).update_product, product_id, {"brand": None})
    except NosiFitAPIError as exc:
        await callback.message.answer(str(exc))
        return
    await state.set_state(None)
    await _send_my_product(callback.message, callback.from_user.id, product_id, edit=True, prefix="✅ Бренд прибрано.\n\n")


# ---------- Saved dishes ("Мої страви") ----------
#
# A dish is a template. Picking it fills the meal draft with its components;
# "✏️ Змінити" lets the user change amounts, remove, replace or add products
# for this meal only, and saving logs the draft in one request. The template
# itself changes only through "♻️ Оновити страву".


def _format_dish(dish: dict) -> str:
    lines = [f"🍲 <b>{html.escape(dish.get('name', 'Страва'))}</b>", ""]
    for item in dish.get("items", []):
        unit = UNIT_LABELS.get(item.get("unit", "g"), item.get("unit", "g"))
        archived = "" if item.get("is_active", True) else " <i>(продукт видалено)</i>"
        lines.append(
            f"• {html.escape(item.get('name', 'Продукт'))} — "
            f"{_format_number(float(item.get('amount') or 0))} {unit}{archived}"
        )
    totals = dish.get("totals", {})
    lines.extend([
        "",
        f"🔥 {totals.get('calories', 0):.0f} ккал · 🥩 {totals.get('protein', 0):.1f} г · "
        f"🥑 {totals.get('fat', 0):.1f} г · 🍞 {totals.get('carbs', 0):.1f} г",
        f"🌾 Клітковина: {_nutrient_text(totals.get('fiber'), totals.get('fiber_complete', True))}"
        f" · 🍬 Цукор: {_nutrient_text(totals.get('sugar'), totals.get('sugar_complete', True))}",
    ])
    return "\n".join(lines)


async def _show_dishes(callback: CallbackQuery, state: FSMContext, offset: int = 0) -> None:
    data = await state.get_data()
    dishes = list(data.get("dishes", [])) if offset else []
    try:
        page, has_more = await asyncio.to_thread(
            _api(callback.from_user.id).list_dishes, "uk", DISHES_PAGE, offset
        )
    except NosiFitAPIError as exc:
        await callback.message.answer(f"Не вдалося завантажити страви: {exc}")
        return
    dishes.extend(page)
    # Cached for the preview: opening a dish needs no request.
    await state.update_data(dishes=dishes)
    if dishes:
        text = (
            "🍲 <b>Мої страви</b>\n\n"
            "Нещодавні — зверху. Натисніть страву, щоб переглянути склад."
        )
    else:
        text = (
            "🍲 <b>Мої страви</b>\n\n"
            "Збережених страв поки немає. Натисніть «➕ Нова страва», "
            "щоб скласти свою, — наступного разу вистачить одного натискання."
        )
    await _safe_edit(
        callback.message,
        text,
        reply_markup=dishes_keyboard(dishes, offset=offset, has_more=has_more),
    )


async def _get_dish(callback: CallbackQuery, state: FSMContext, dish_id: int) -> dict | None:
    data = await state.get_data()
    dish = next((item for item in data.get("dishes", []) if item.get("id") == dish_id), None)
    if dish is not None:
        return dish
    try:
        return await asyncio.to_thread(_api(callback.from_user.id).get_dish, dish_id)
    except NosiFitAPIError as exc:
        await callback.message.answer(str(exc))
        return None


async def _load_dish_into_draft(state: FSMContext, dish: dict) -> bool:
    """Append the dish components to the draft; True if the draft is the dish."""
    data = await state.get_data()
    pending = list(data.get("pending", []))
    is_dish_only = not pending
    pending.extend(
        _pending_item(item, float(item["amount"]), item["unit"])
        for item in dish.get("items", [])
    )
    await state.update_data(
        pending=pending,
        editing_index=None,
        # Entries are tagged with the dish only when the draft is that dish.
        draft_dish_id=dish["id"] if is_dish_only else None,
        draft_dish_name=dish.get("name") if is_dish_only else None,
    )
    return is_dish_only


async def _continue_with_draft(callback: CallbackQuery, state: FSMContext) -> None:
    if (await state.get_data()).get("category"):
        await _show_review(callback.message, state, edit=True)
        return
    await state.set_state(NutritionStates.choosing_meal)
    await _safe_edit(
        callback.message,
        "До якого прийому їжі додати?",
        reply_markup=meal_categories(),
    )


@router.callback_query(F.data == "nutrition:dishes")
async def dishes(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _show_dishes(callback, state)


@router.callback_query(F.data.startswith("nutrition:dishes_more:"))
async def dishes_more(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _show_dishes(callback, state, int(callback.data.rsplit(":", 1)[1]))


@router.callback_query(F.data.startswith("nutrition:dish:"))
async def dish_view(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    dish = await _get_dish(callback, state, int(callback.data.rsplit(":", 1)[1]))
    if dish is None:
        return
    await _safe_edit(callback.message, _format_dish(dish), reply_markup=dish_keyboard(dish["id"]))


@router.callback_query(F.data.startswith("nutrition:dish_add:"))
async def dish_add(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    dish = await _get_dish(callback, state, int(callback.data.rsplit(":", 1)[1]))
    if dish is None:
        return
    data = await state.get_data()
    category = data.get("category")
    if category and not data.get("pending"):
        # Fast path: the meal is known and the draft is empty, so the dish
        # is logged as saved in a single request.
        try:
            result = await asyncio.to_thread(
                _api(callback.from_user.id).log_food,
                category,
                None,
                dish_id=dish["id"],
                time=data.get("meal_time"),
            )
        except NosiFitAPIError as exc:
            await callback.message.answer(f"Не вдалося додати страву: {exc}")
            return
        await state.clear()
        await _safe_edit(
            callback.message,
            f"✅ <b>{html.escape(dish['name'])}</b> додано.\n\n" + _format_day(result["day"]),
            reply_markup=nutrition_menu(),
        )
        return
    await _load_dish_into_draft(state, dish)
    await _continue_with_draft(callback, state)


@router.callback_query(F.data.startswith("nutrition:dish_edit:"))
async def dish_edit(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    dish = await _get_dish(callback, state, int(callback.data.rsplit(":", 1)[1]))
    if dish is None:
        return
    await _load_dish_into_draft(state, dish)
    await _continue_with_draft(callback, state)


@router.callback_query(F.data.startswith("nutrition:dish_delete:"))
async def dish_delete(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    dish_id = int(callback.data.rsplit(":", 1)[1])
    await _safe_edit(
        callback.message,
        "Видалити цю страву?\n\nУже записані прийоми їжі не зміняться.",
        reply_markup=dish_delete_keyboard(dish_id),
    )


@router.callback_query(F.data.startswith("nutrition:dish_delete_yes:"))
async def dish_delete_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    dish_id = int(callback.data.rsplit(":", 1)[1])
    try:
        await asyncio.to_thread(_api(callback.from_user.id).delete_dish, dish_id)
    except NosiFitAPIError as exc:
        if getattr(exc, "code", None) != "dish_not_found":
            await callback.message.answer(str(exc))
            return
    data = await state.get_data()
    if data.get("draft_dish_id") == dish_id:
        await state.update_data(draft_dish_id=None, draft_dish_name=None)
    await _show_dishes(callback, state)


@router.callback_query(NutritionStates.reviewing, F.data.startswith("nutrition:replace:"))
async def replace_pending_item(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    index = int(callback.data.rsplit(":", 1)[1])
    pending = (await state.get_data()).get("pending", [])
    if index < 0 or index >= len(pending):
        await callback.message.answer("Цю позицію вже видалено.")
        return
    # The next product picked takes this line's place (see enter_amount).
    await state.update_data(editing_index=index)
    await state.set_state(NutritionStates.searching_product)
    await _safe_edit(
        callback.message,
        f"🔁 <b>Заміна: {html.escape(pending[index].get('name', 'Продукт'))}</b>\n\n"
        "Напишіть назву продукту, яким замінити.",
        reply_markup=catalog_keyboard(),
    )


def _draft_items(pending: list[dict]) -> list[dict]:
    return [
        {"product_id": item["product_id"], "amount": item["amount"], "unit": item["unit"]}
        for item in pending
    ]


@router.callback_query(NutritionStates.reviewing, F.data == "nutrition:save_dish")
async def save_draft_as_dish(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(NutritionStates.naming_dish)
    await callback.message.answer(
        "💾 Як назвати страву? Наприклад, <b>Моя вівсянка</b>.",
        reply_markup=my_product_cancel_keyboard(),
    )


@router.message(NutritionStates.naming_dish)
async def name_dish(message: Message, state: FSMContext) -> None:
    name = " ".join((message.text or "").split())
    if not name or len(name) > 120:
        await message.answer("Назва страви — від 1 до 120 символів.")
        return
    data = await state.get_data()
    if data.get("building_dish"):
        await state.update_data(dish_builder_name=name)
        if data.get("pending"):
            # Renamed after "name already taken": save right away.
            await _save_dish_builder(message, message.from_user.id, state)
            return
        await state.set_state(NutritionStates.searching_product)
        await message.answer(
            f"🍲 <b>{html.escape(name)}</b>\n\n"
            "Додайте продукти: напишіть назву першого, наприклад <b>вівсяні пластівці</b>.",
            reply_markup=catalog_keyboard(),
        )
        return
    try:
        dish = await asyncio.to_thread(
            _api(message.from_user.id).create_dish, name, _draft_items(data.get("pending", []))
        )
    except NosiFitAPIError as exc:
        await message.answer(f"Не вдалося зберегти страву: {exc}")
        return
    # The draft is now this dish: saving the meal tags its entries with it.
    await state.update_data(draft_dish_id=dish["id"], draft_dish_name=dish["name"], dishes=[])
    await message.answer(f"✅ Страву «{html.escape(dish['name'])}» збережено в «Мої страви».")
    await _show_review(message, state)


@router.callback_query(NutritionStates.reviewing, F.data == "nutrition:update_dish")
async def update_dish_from_draft(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    dish_id = data.get("draft_dish_id")
    if not dish_id:
        await callback.answer()
        return
    try:
        await asyncio.to_thread(
            _api(callback.from_user.id).update_dish,
            int(dish_id),
            {"items": _draft_items(data.get("pending", []))},
        )
    except NosiFitAPIError as exc:
        await callback.answer()
        await callback.message.answer(f"Не вдалося оновити страву: {exc}")
        return
    await state.update_data(dishes=[])
    await callback.answer("♻️ Страву оновлено", show_alert=False)


# ---------- New dish from «Мої страви» and the back buttons ----------


def _format_new_dish(name: str, pending: list[dict]) -> str:
    lines = [f"🍲 <b>Нова страва «{html.escape(name)}»</b>"]
    if not pending:
        lines.extend(["", "Поки без продуктів. Натисніть «➕ Додати продукт»."])
        return "\n".join(lines)
    lines.append("")
    for index, item in enumerate(pending, start=1):
        unit = UNIT_LABELS.get(item["unit"], item["unit"])
        lines.append(f"{index}. {html.escape(item['name'])} — {_format_number(item['amount'])} {unit}")
    totals = _pending_totals(pending)
    lines.extend([
        "",
        f"🔥 {totals['calories']:.0f} ккал · 🥩 {totals['protein']:.1f} г · "
        f"🥑 {totals['fat']:.1f} г · 🍞 {totals['carbs']:.1f} г",
        f"🌾 Клітковина: {_nutrient_text(totals['fiber'], totals['fiber_complete'])}"
        f" · 🍬 Цукор: {_nutrient_text(totals['sugar'], totals['sugar_complete'])}",
    ])
    return "\n".join(lines)


def _new_dish_name_keyboard():
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="← Мої страви", callback_data="nutrition:dishes"),
        InlineKeyboardButton(text="✕ Скасувати", callback_data="nutrition:cancel"),
    ]])


@router.callback_query(F.data == "nutrition:dish_new")
async def new_dish(callback: CallbackQuery, state: FSMContext) -> None:
    """➕ Нова страва: name, then products, then save — no meal involved."""
    await callback.answer()
    await state.update_data(
        building_dish=True,
        dish_builder_name=None,
        pending=[],
        editing_index=None,
        draft_dish_id=None,
        draft_dish_name=None,
    )
    await state.set_state(NutritionStates.naming_dish)
    await _safe_edit(
        callback.message,
        "🍲 <b>Нова страва</b>\n\nЯк її назвати? Наприклад, <b>Моя вівсянка</b>.",
        reply_markup=_new_dish_name_keyboard(),
    )


async def _save_dish_builder(message: Message, user_id: int, state: FSMContext, *, edit: bool = False) -> None:
    data = await state.get_data()
    try:
        dish = await asyncio.to_thread(
            _api(user_id).create_dish,
            data.get("dish_builder_name") or "",
            _draft_items(data.get("pending", [])),
        )
    except NosiFitAPIError as exc:
        if getattr(exc, "code", None) == "duplicate_dish":
            # Keep the products, ask only for another name.
            await state.set_state(NutritionStates.naming_dish)
            await message.answer(f"{exc}\nНапишіть іншу назву.", reply_markup=_new_dish_name_keyboard())
            return
        await message.answer(f"Не вдалося зберегти страву: {exc}")
        return
    await state.update_data(
        building_dish=False, dish_builder_name=None, pending=[], editing_index=None, dishes=[]
    )
    await state.set_state(None)
    text = "✅ Страву збережено в «Мої страви».\n\n" + _format_dish(dish)
    if edit:
        await _safe_edit(message, text, reply_markup=dish_keyboard(dish["id"]))
    else:
        await message.answer(text, reply_markup=dish_keyboard(dish["id"]))


@router.callback_query(NutritionStates.reviewing, F.data == "nutrition:dish_builder_save")
async def save_new_dish(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _save_dish_builder(callback.message, callback.from_user.id, state, edit=True)


@router.callback_query(F.data == "nutrition:meal_back")
async def meal_back(callback: CallbackQuery, state: FSMContext) -> None:
    """From the meal time back to choosing the meal; picked products stay."""
    await callback.answer()
    await state.set_state(NutritionStates.choosing_meal)
    await _safe_edit(
        callback.message,
        "🍽 <b>Додати їжу</b>\n\nОберіть прийом їжі:",
        reply_markup=meal_categories(),
    )


@router.callback_query(F.data == "nutrition:catalog_back_to_products")
async def review_back(callback: CallbackQuery, state: FSMContext) -> None:
    """From the list being added back to picking products."""
    await callback.answer()
    await _show_product_menu(callback, state)


@router.callback_query(F.data.in_({"nutrition:step_back", "nutrition:catalog_back"}))
async def step_back(callback: CallbackQuery, state: FSMContext) -> None:
    """One step back from wherever the user is, keeping what they picked.

    Products already chosen (for a meal or a new dish) → that list; a meal
    chosen without products → from the catalog to the meal choice, from a
    deeper step to the catalog; nothing chosen → the nutrition menu.
    """
    await callback.answer()
    data = await state.get_data()
    if data.get("pending") or (data.get("building_dish") and data.get("dish_builder_name")):
        await state.update_data(editing_index=None)
        await _show_review(callback.message, state, edit=True)
        return
    if data.get("category"):
        if callback.data == "nutrition:catalog_back":
            await meal_back(callback, state)
        else:
            await _show_product_menu(callback, state)
        return
    await back_to_nutrition(callback, state)


# After the menu handler: reply-keyboard buttons keep working while scanning.
@router.message(NutritionStates.scanning_barcode)
async def barcode_typed(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if looks_like_barcode(text):
        await _barcode_lookup(message, state, text)
        return
    if text:
        # A name instead of digits: search the catalog as usual.
        await _perform_product_search(message, state, text, offset=0)
        return
    await message.answer(BARCODE_SCAN_TEXT, reply_markup=barcode_scan_keyboard())
