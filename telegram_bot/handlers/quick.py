"""Quick entries: food in three taps, sleep in two, and the "Log" and "More" menus.

Food: the meal comes from the time of day (or from the card's button), recent
and favourite foods are buttons, an amount is a button, and the entry is saved
at once with "Undo" instead of a review step. Typing a name searches; a photo
of a barcode goes to the barcode flow of handlers/nutrition.py.
"""

import asyncio
import html
import re
from datetime import datetime, time, timedelta

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from telegram_bot import i18n
from telegram_bot.handlers.auth import log_out
from telegram_bot.handlers.language import choose_language
from telegram_bot.handlers.nutrition import show_day
from telegram_bot.handlers.today import refresh_card
from telegram_bot.handlers.training import show_training, start_add_exercise
from telegram_bot.handlers.water import _show as show_water
from telegram_bot.handlers.weight import ask_weight
from telegram_bot.i18n import t
from telegram_bot.keyboards.main import LOG, MENU_TEXTS, MORE, button, main_menu
from telegram_bot.keyboards.nutrition import UNIT_LABELS, meal_name
from telegram_bot.runtime import get_api, is_authenticated, local_now
from telegram_bot.services.api import NosiFitAPIError
from telegram_bot.states.quick import QuickStates
from telegram_bot.widgets.state import meal_for_hour, number

router = Router()

MEALS = ("breakfast", "lunch", "dinner", "snack")
SHOWN = 6
AMOUNTS = {"g": (100, 150, 200), "ml": (100, 200, 250), "pcs": (1, 2, 3)}
MAX_AMOUNT = {"g": 5000.0, "ml": 5000.0, "pcs": 100.0}
BEDTIMES = ("22:00", "22:30", "23:00", "23:30", "00:00", "00:30")
WAKE_TIMES = ("06:00", "06:30", "07:00", "07:30", "08:00", "08:30")
TIME = re.compile(r"([01]?\d|2[0-3])[:.]([0-5]\d)")


def _rows(buttons: list[InlineKeyboardButton], width: int) -> list[list[InlineKeyboardButton]]:
    return [buttons[i:i + width] for i in range(0, len(buttons), width)]


def _button(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


async def _edit(message: Message, text: str, markup: InlineKeyboardMarkup | None = None) -> None:
    try:
        await message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as exc:
        if "not modified" not in str(exc).lower():
            await message.answer(text, reply_markup=markup)


# --- Log and More ---------------------------------------------------------------------------


def log_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_button(t("m.food"), "qf:m:auto"), _button(t("m.sleep"), "sl:s")],
        [_button(t("m.water"), "rec:water"), _button(t("m.weight"), "today:weight"), _button(t("m.workout"), "today:workout")],
    ])


def more_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_button(t("m.nutrition"), "more:nutrition")],
        [_button(t("m.training"), "more:training")],
        [_button(t("m.language"), "more:language"), _button(t("m.logout"), "more:logout")],
    ])


@router.message(button(LOG))
async def log_button(message: Message, state: FSMContext) -> None:
    await state.clear()
    if not is_authenticated(message.from_user.id):
        await message.answer(t("err.login_start"), reply_markup=main_menu(authenticated=False))
        return
    await message.answer(t("m.log_title"), reply_markup=log_menu())


@router.message(button(MORE))
async def more_button(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(t("m.more_title"), reply_markup=more_menu())


@router.callback_query(F.data == "rec:water")
async def log_water(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await show_water(callback.message, callback.from_user.id)


@router.callback_query(F.data.startswith("more:"))
async def more_choice(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    choice = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id
    if choice == "nutrition":
        await state.clear()
        await show_day(callback.message, user_id)
    elif choice == "training":
        await show_training(callback.message, state, user_id)
    elif choice == "language":
        await choose_language(callback.message)
    elif choice == "logout":
        await log_out(callback.message, state, user_id)


# --- Food in three taps ---------------------------------------------------------------------


def _product(product: dict) -> dict:
    """What the flow keeps of a product between taps."""
    return {
        "name": str(product.get("name") or t("nu.product_default"))[:64],
        "unit": product.get("default_unit") if product.get("default_unit") in AMOUNTS else "g",
        "kcal": float(product.get("kcal_per_100g") or 0),
        "gpu": float(product.get("grams_per_unit") or 1),
    }


def _products_keyboard(products: dict) -> InlineKeyboardMarkup:
    buttons = [_button(item["name"], f"qf:p:{pid}") for pid, item in products.items()]
    return InlineKeyboardMarkup(inline_keyboard=_rows(buttons, 2))


async def start_food(message: Message, state: FSMContext, user_id: int, meal: str) -> None:
    """Ask what to add to ``meal`` ("auto": the meal of the hour)."""
    if meal not in MEALS:
        meal = meal_for_hour(local_now().hour)
    api = get_api(user_id)
    try:
        recent = await asyncio.to_thread(api.get_recent_products, i18n.current_language(), SHOWN)
        favorites = await asyncio.to_thread(api.get_favorite_products, i18n.current_language(), SHOWN)
    except NosiFitAPIError:
        recent, favorites = [], []
    products: dict[str, dict] = {}
    for product in [*recent, *favorites]:
        if isinstance(product.get("id"), int) and str(product["id"]) not in products:
            products[str(product["id"])] = _product(product)
    products = dict(list(products.items())[:SHOWN])

    await state.set_state(QuickStates.food_search)
    await state.update_data(qf_meal=meal, qf_products=products)
    name = html.escape(meal_name(meal))
    if products:
        await message.answer(t("q.title", meal=name), reply_markup=_products_keyboard(products))
    else:
        await message.answer(t("q.title_empty", meal=name))


@router.callback_query(F.data.startswith("qf:m:") | (F.data == "today:food"))
async def food_for_meal(callback: CallbackQuery, state: FSMContext) -> None:
    """``today:food`` comes from cards sent before the buttons followed the step."""
    await callback.answer()
    await state.clear()
    meal = callback.data.split(":", 2)[2] if callback.data.startswith("qf:m:") else "auto"
    await start_food(callback.message, state, callback.from_user.id, meal)


@router.message(QuickStates.food_search, F.text, ~F.text.in_(MENU_TEXTS), ~F.text.startswith("/"))
async def food_search(message: Message, state: FSMContext) -> None:
    query = message.text.strip()[:64]
    data = await state.get_data()
    meal = data.get("qf_meal") or meal_for_hour(local_now().hour)
    try:
        found = await asyncio.to_thread(get_api(message.from_user.id).search_products, query, i18n.current_language(), SHOWN)
    except NosiFitAPIError as exc:
        await message.answer(t("q.failed", error=exc))
        return
    products = {str(p["id"]): _product(p) for p in found if isinstance(p.get("id"), int)}
    if not products:
        await message.answer(t("q.none", query=html.escape(query)))
        return
    await state.update_data(qf_products={**data.get("qf_products", {}), **products})
    await message.answer(
        t("q.found", meal=html.escape(meal_name(meal)), query=html.escape(query)),
        reply_markup=_products_keyboard(products),
    )


def _amount_label(amount: float, unit: str) -> str:
    return f"{number(amount, 1)} {UNIT_LABELS.get(unit, unit)}"


@router.callback_query(F.data.startswith("qf:p:"))
async def food_product(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = await state.get_data()
    product = (data.get("qf_products") or {}).get(callback.data.split(":", 2)[2])
    if product is None or not data.get("qf_meal"):
        await callback.message.answer(t("q.gone"))
        return
    await state.update_data(qf_pick=callback.data.split(":", 2)[2])
    unit = product["unit"]
    buttons = [_button(_amount_label(a, unit), f"qf:a:{a}") for a in AMOUNTS[unit]]
    markup = InlineKeyboardMarkup(inline_keyboard=[buttons, [_button(t("q.other"), "qf:o")]])
    await callback.message.answer(t("q.how_much", name=html.escape(product["name"])), reply_markup=markup)


@router.callback_query(F.data == "qf:o")
async def food_other_amount(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = await state.get_data()
    product = (data.get("qf_products") or {}).get(data.get("qf_pick") or "")
    if product is None:
        await callback.message.answer(t("q.gone"))
        return
    await state.set_state(QuickStates.food_amount)
    example = "1" if product["unit"] == "pcs" else "120"
    await callback.message.answer(t("q.type_amount", unit=UNIT_LABELS[product["unit"]], example=example))


@router.callback_query(F.data.startswith("qf:a:"))
async def food_amount_button(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    try:
        amount = float(callback.data.split(":", 2)[2])
    except ValueError:
        return
    await _log_food(callback.message, state, callback.from_user.id, amount, edit=True)


@router.message(QuickStates.food_amount, F.text)
async def food_amount_typed(message: Message, state: FSMContext) -> None:
    match = re.search(r"\d+(?:[.,]\d+)?", message.text or "")
    amount = float(match.group().replace(",", ".")) if match else 0
    await _log_food(message, state, message.from_user.id, amount, edit=False)


async def _log_food(message: Message, state: FSMContext, user_id: int, amount: float, *, edit: bool) -> None:
    data = await state.get_data()
    pick = data.get("qf_pick") or ""
    product = (data.get("qf_products") or {}).get(pick)
    meal = data.get("qf_meal")
    if product is None or meal not in MEALS:
        await message.answer(t("q.gone"))
        return
    unit = product["unit"]
    if not 0 < amount <= MAX_AMOUNT[unit]:
        example = "1" if unit == "pcs" else "120"
        await message.answer(t("q.type_amount", unit=UNIT_LABELS[unit], example=example))
        return
    try:
        result = await asyncio.to_thread(
            get_api(user_id).log_food, meal, [{"product_id": int(pick), "amount": amount, "unit": unit}]
        )
    except NosiFitAPIError as exc:
        await message.answer(t("q.failed", error=exc))
        return

    grams = amount * product["gpu"] if unit == "pcs" else amount
    ids = ".".join(str(i) for i in result.get("ids", []) if isinstance(i, int))
    text = t(
        "q.added",
        meal=html.escape(meal_name(meal)),
        name=html.escape(product["name"]),
        amount=_amount_label(amount, unit),
        kcal=number(product["kcal"] * grams / 100),
    )
    row = [_button(t("q.undo"), f"qf:u:{ids}")] if ids else []
    markup = InlineKeyboardMarkup(inline_keyboard=[row + [_button(t("q.more"), f"qf:m:{meal}")]])
    await state.set_state(QuickStates.food_search)
    await state.update_data(qf_undo={ids: product["name"]})
    if edit:
        await _edit(message, text, markup)
    else:
        await message.answer(text, reply_markup=markup)
    await refresh_card(message.bot, message.chat.id, user_id)


@router.callback_query(F.data.startswith("qf:u:"))
async def food_undo(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    raw = callback.data.split(":", 2)[2]
    ids = [int(part) for part in raw.split(".") if part.isdigit()][:20]
    api = get_api(callback.from_user.id)
    try:
        for entry_id in ids:
            await asyncio.to_thread(api.delete_entry, entry_id)
    except NosiFitAPIError as exc:
        await callback.message.answer(t("q.failed", error=exc))
        return
    name = ((await state.get_data()).get("qf_undo") or {}).get(raw) or t("nu.product_default")
    await _edit(callback.message, t("q.undone", name=html.escape(name)))
    await refresh_card(callback.message.bot, callback.message.chat.id, callback.from_user.id)


# --- Sleep in two taps ------------------------------------------------------------------------


def _times_keyboard(times: tuple[str, ...], prefix: str, other: str) -> InlineKeyboardMarkup:
    buttons = [_button(value, f"{prefix}{value.replace(':', '')}") for value in times]
    return InlineKeyboardMarkup(inline_keyboard=[*_rows(buttons, 3), [_button(t("s.other"), other)]])


def _clock(value: str) -> time | None:
    match = TIME.fullmatch((value or "").strip()) or (
        re.fullmatch(r"(\d{2})(\d{2})", value or "") if value and len(value) == 4 else None
    )
    if not match:
        return None
    hour, minute = int(match.group(1)), int(match.group(2))
    return time(hour, minute) if hour < 24 and minute < 60 else None


def night(bed: time, wake: time, now: datetime) -> tuple[datetime, datetime]:
    """The night that ended most recently at ``wake``: a bedtime later than the
    wake time (or equal) was the evening before."""
    end = now.replace(hour=wake.hour, minute=wake.minute, second=0, microsecond=0)
    if end > now:
        end -= timedelta(days=1)
    start = end.replace(hour=bed.hour, minute=bed.minute)
    if start >= end:
        start -= timedelta(days=1)
    return start, end


async def start_sleep(message: Message, state: FSMContext) -> None:
    await state.set_state(QuickStates.sleep_bed)
    await message.answer(t("s.bed"), reply_markup=_times_keyboard(BEDTIMES, "sl:b:", "sl:bo"))


@router.callback_query(F.data == "sl:s")
async def sleep_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await start_sleep(callback.message, state)


@router.callback_query(F.data == "sl:bo")
async def sleep_bed_other(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(QuickStates.sleep_bed)
    await callback.message.answer(t("s.type"))


async def _ask_wake(message: Message, state: FSMContext, bed: time, *, edit: bool) -> None:
    await state.set_state(QuickStates.sleep_wake)
    await state.update_data(sl_bed=bed.strftime("%H:%M"))
    stamp = bed.strftime("%H%M")
    text = t("s.wake", bed=bed.strftime("%H:%M"))
    markup = _times_keyboard(WAKE_TIMES, f"sl:w:{stamp}:", f"sl:wo:{stamp}")
    if edit:
        await _edit(message, text, markup)
    else:
        await message.answer(text, reply_markup=markup)


@router.callback_query(F.data.startswith("sl:b:"))
async def sleep_bed(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    bed = _clock(callback.data.split(":", 2)[2])
    if bed is not None:
        await _ask_wake(callback.message, state, bed, edit=True)


@router.message(QuickStates.sleep_bed, F.text, ~F.text.in_(MENU_TEXTS), ~F.text.startswith("/"))
async def sleep_bed_typed(message: Message, state: FSMContext) -> None:
    bed = _clock(message.text)
    if bed is None:
        await message.answer(t("s.bad_time"))
        return
    await _ask_wake(message, state, bed, edit=False)


@router.callback_query(F.data.startswith("sl:wo:"))
async def sleep_wake_other(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    bed = _clock(callback.data.split(":", 2)[2])
    if bed is None:
        return
    await state.set_state(QuickStates.sleep_wake)
    await state.update_data(sl_bed=bed.strftime("%H:%M"))
    await callback.message.answer(t("s.type"))


@router.callback_query(F.data.startswith("sl:w:"))
async def sleep_wake(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    parts = callback.data.split(":")
    bed, wake = (_clock(parts[2]), _clock(parts[3])) if len(parts) == 4 else (None, None)
    if bed is not None and wake is not None:
        await _log_sleep(callback.message, state, callback.from_user.id, bed, wake, edit=True)


@router.message(QuickStates.sleep_wake, F.text, ~F.text.in_(MENU_TEXTS), ~F.text.startswith("/"))
async def sleep_wake_typed(message: Message, state: FSMContext) -> None:
    wake = _clock(message.text)
    bed = _clock((await state.get_data()).get("sl_bed") or "")
    if wake is None or bed is None:
        await message.answer(t("s.bad_time"))
        return
    await _log_sleep(message, state, message.from_user.id, bed, wake, edit=False)


async def _log_sleep(message: Message, state: FSMContext, user_id: int, bed: time, wake: time, *, edit: bool) -> None:
    start, end = night(bed, wake, local_now())
    try:
        await asyncio.to_thread(get_api(user_id).add_sleep, start.isoformat(), end.isoformat())
    except NosiFitAPIError as exc:
        await message.answer(t("s.failed", error=exc))
        return
    await state.clear()
    minutes = int((end - start).total_seconds() // 60)
    text = t(
        "s.saved",
        duration=t("w.sleep", h=minutes // 60, m=minutes % 60),
        start=start.strftime("%H:%M"),
        end=end.strftime("%H:%M"),
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[[_button(t("s.change"), "sl:s")]])
    if edit:
        await _edit(message, text, markup)
    else:
        await message.answer(text, reply_markup=markup)
    await refresh_card(message.bot, message.chat.id, user_id)
