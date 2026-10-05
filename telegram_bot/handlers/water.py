import asyncio
import re

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from telegram_bot.keyboards.body import cancel_keyboard, water_keyboard
from telegram_bot.keyboards.main import WATER, main_menu
from telegram_bot.runtime import get_api, is_authenticated
from telegram_bot.services.api import NosiFitAPIError
from telegram_bot.states.body import WaterStates


router = Router()

MIN_LITERS = 0.05
MAX_LITERS = 5.0


def _format_liters(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _water_text(data: dict, prefix: str = "") -> str:
    amount = float(data.get("amount") or 0)
    recommended = float(data.get("recommended") or 0)
    lines = [prefix + "💧 <b>Вода сьогодні</b>", ""]
    if recommended > 0:
        percent = round(amount / recommended * 100)
        lines.append(f"{_format_liters(amount)} / {_format_liters(recommended)} л · {percent}%")
    else:
        lines.append(f"{_format_liters(amount)} л")
    lines.extend([
        "",
        "Напої з харчування (кава, сік, молоко) враховуються автоматично.",
        "Оберіть, скільки додати:",
    ])
    return "\n".join(lines)


def _parse_liters(text: str) -> float | None:
    value = (text or "").strip().lower().replace(",", ".").replace(" ", "")
    match = re.fullmatch(r"([+\-−]?)(\d+(?:\.\d+)?)(мл|ml|л|l)?", value)
    if not match:
        return None
    sign, number, unit = match.groups()
    liters = float(number)
    if unit in ("мл", "ml"):
        liters /= 1000
    elif unit is None and liters > MAX_LITERS:
        # "250" almost certainly means millilitres.
        liters /= 1000
    if sign in ("-", "−"):
        liters = -liters
    if not (MIN_LITERS <= abs(liters) <= MAX_LITERS):
        return None
    return liters


async def _show(message: Message, user_id: int, *, edit: bool = False, prefix: str = "") -> None:
    try:
        data = await asyncio.to_thread(get_api(user_id).get_water)
    except NosiFitAPIError as exc:
        await message.answer(str(exc))
        return
    text = _water_text(data, prefix)
    if edit:
        try:
            await message.edit_text(text, reply_markup=water_keyboard())
            return
        except TelegramBadRequest:
            pass
    await message.answer(text, reply_markup=water_keyboard())


@router.message(F.text == WATER)
async def water(message: Message, state: FSMContext) -> None:
    await state.clear()
    if not is_authenticated(message.from_user.id):
        await message.answer(
            "Спочатку увійдіть у NosiFit.",
            reply_markup=main_menu(authenticated=False),
        )
        return
    await _show(message, message.from_user.id)


@router.callback_query(F.data.startswith("water:add:"))
async def add_preset(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    try:
        liters = float(callback.data.rsplit(":", 1)[1])
        await asyncio.to_thread(get_api(callback.from_user.id).add_water, liters)
    except (ValueError, NosiFitAPIError) as exc:
        await callback.message.answer(str(exc))
        return
    sign = "+" if liters > 0 else "−"
    await _show(
        callback.message,
        callback.from_user.id,
        edit=True,
        prefix=f"✅ {sign}{_format_liters(abs(liters))} л\n\n",
    )


@router.callback_query(F.data == "water:custom")
async def custom_amount(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(WaterStates.entering_amount)
    await callback.message.answer(
        "Введіть кількість, наприклад <b>0,4</b> (л) або <b>300 мл</b>.\n"
        "Щоб відняти помилковий запис — з мінусом: <b>-0,25</b>.",
        reply_markup=cancel_keyboard("water"),
    )


@router.message(WaterStates.entering_amount)
async def enter_amount(message: Message, state: FSMContext) -> None:
    liters = _parse_liters(message.text or "")
    if liters is None:
        await message.answer(
            "Не вдалося розпізнати кількість. Введіть від 0,05 до 5 л, "
            "наприклад <b>0,5</b> або <b>250 мл</b>.",
            reply_markup=cancel_keyboard("water"),
        )
        return
    try:
        await asyncio.to_thread(get_api(message.from_user.id).add_water, liters)
    except NosiFitAPIError as exc:
        await message.answer(str(exc))
        return
    await state.clear()
    sign = "+" if liters > 0 else "−"
    await _show(message, message.from_user.id, prefix=f"✅ {sign}{_format_liters(abs(liters))} л\n\n")


@router.callback_query(F.data == "water:cancel")
async def cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    try:
        await callback.message.edit_text("Дію скасовано.")
    except TelegramBadRequest:
        pass
