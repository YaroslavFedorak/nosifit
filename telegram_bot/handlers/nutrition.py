import asyncio
import html
import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from telegram_bot.keyboards.main import NUTRITION, main_menu
from telegram_bot.keyboards.nutrition import (
    meal_categories,
    nutrition_menu,
    product_results,
    review_keyboard,
)
from telegram_bot.services.api import NosiFitAPIError
from telegram_bot.services.nutrition import get_or_create_meal
from telegram_bot.states.nutrition import NutritionStates


router = Router()


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


def _format_pending(category: str, pending: list[dict]) -> str:
    lines = [f"🍽 <b>{html.escape(category)}</b>", "", "Додано:"]
    for item in pending:
        unit_label = "шт." if item["unit"] == "pcs" else item["unit"]
        lines.append(
            f"✓ {html.escape(item['name'])} — {_format_number(item['amount'])} {unit_label}"
        )
    return "\n".join(lines)


@router.message(F.text == NUTRITION)
async def nutrition(message: Message, state: FSMContext) -> None:
    await state.clear()
    try:
        day = await asyncio.to_thread(_api(message.from_user.id).get_day)
    except NosiFitAPIError as exc:
        await message.answer(
            f"Не вдалося підключитися до NosiFit: {exc}",
            reply_markup=main_menu(),
        )
        return

    await message.answer(_format_day(day), reply_markup=nutrition_menu())


@router.callback_query(F.data == "nutrition:add")
async def add_food(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
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
    await state.update_data(category=category, pending=[])
    await state.set_state(NutritionStates.searching_product)
    await callback.message.edit_text(
        f"🍽 <b>{category}</b>\n\n"
        "Напишіть назву продукту для пошуку.\n"
        "Наприклад: <i>рис</i>, <i>куряча грудка</i>, <i>банан</i>.",
    )


@router.message(NutritionStates.searching_product)
async def search_product(message: Message, state: FSMContext) -> None:
    query = (message.text or "").strip()
    if not query:
        await message.answer("Введіть назву продукту.")
        return

    try:
        products = await asyncio.to_thread(_api(message.from_user.id).search_products, query)
    except NosiFitAPIError as exc:
        await message.answer(f"Не вдалося виконати пошук: {exc}")
        return

    if not products:
        await message.answer(
            "Нічого не знайдено. Спробуйте коротшу назву або інший запит."
        )
        return

    await message.answer(
        f"🔎 <b>{html.escape(query)}</b>\n\nОберіть продукт:",
        reply_markup=product_results(products),
    )


@router.callback_query(
    NutritionStates.searching_product,
    F.data.startswith("nutrition:product:"),
)
async def choose_product(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    product_id = int(callback.data.rsplit(":", 1)[1])

    try:
        product = await asyncio.to_thread(_api(callback.from_user.id).get_product, product_id)
    except NosiFitAPIError as exc:
        await callback.message.answer(f"Не вдалося завантажити продукт: {exc}")
        return

    unit = product.get("default_unit") or "g"
    default_amount = 1 if unit == "pcs" else 100

    await state.update_data(
        product_id=product_id,
        product_name=product.get("name", "Продукт"),
        product_unit=unit,
    )
    await state.set_state(NutritionStates.entering_amount)

    unit_label = "шт." if unit == "pcs" else unit
    await callback.message.edit_text(
        f"🍽 <b>{html.escape(product.get('name', 'Продукт'))}</b>\n\n"
        f"На 100 г: {product.get('kcal_per_100g', 0):.0f} kcal · "
        f"{product.get('protein_per_100g', 0):.1f} г білка\n\n"
        f"Введіть кількість у {unit_label}. "
        f"За замовчуванням: <b>{default_amount:g}</b>.",
    )


@router.message(NutritionStates.entering_amount)
async def enter_amount(message: Message, state: FSMContext) -> None:
    amount = _parse_amount(message.text or "")
    if amount is None:
        await message.answer("Введіть додатне число, наприклад 150 або 1,5.")
        return

    data = await state.get_data()
    pending = list(data.get("pending", []))
    pending.append(
        {
            "product_id": data["product_id"],
            "name": data["product_name"],
            "amount": amount,
            "unit": data["product_unit"],
        }
    )
    await state.update_data(pending=pending)
    await state.set_state(NutritionStates.reviewing)

    await message.answer(
        _format_pending(data["category"], pending),
        reply_markup=review_keyboard(),
    )


@router.callback_query(NutritionStates.reviewing, F.data == "nutrition:more")
async def add_more(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(NutritionStates.searching_product)
    data = await state.get_data()
    await callback.message.edit_text(
        f"🍽 <b>{data['category']}</b>\n\n"
        "Напишіть назву наступного продукту.",
    )


@router.callback_query(NutritionStates.reviewing, F.data == "nutrition:save")
async def save_meal(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = await state.get_data()
    pending = data.get("pending", [])
    category = data["category"]

    if not pending:
        await callback.message.answer("У прийомі ще немає продуктів.")
        return

    try:
        api = _api(callback.from_user.id)
        day = await asyncio.to_thread(api.get_day)
        meal = await asyncio.to_thread(get_or_create_meal, api, day, category)

        for item in pending:
            await asyncio.to_thread(
                api.add_entry,
                meal["id"],
                item["product_id"],
                item["amount"],
                item["unit"],
            )

        updated_day = await asyncio.to_thread(api.get_day)
    except NosiFitAPIError as exc:
        await callback.message.answer(f"Не вдалося зберегти прийом: {exc}")
        return

    await state.clear()
    await callback.message.edit_text(
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

    await callback.message.edit_text(_format_day(day), reply_markup=nutrition_menu())


@router.callback_query(F.data == "nutrition:cancel")
async def cancel_nutrition(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await callback.message.edit_text("Дію скасовано.")
    await callback.message.answer("Оберіть дію:", reply_markup=main_menu(authenticated=True))
