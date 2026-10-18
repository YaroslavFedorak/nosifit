import asyncio
import re

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from telegram_bot.i18n import t
from telegram_bot.keyboards.body import cancel_keyboard
from telegram_bot.keyboards.main import WEIGHT, button, main_menu, nutrition_mode_menu
from telegram_bot.runtime import get_api, is_authenticated
from telegram_bot.services.api import NosiFitAPIError
from telegram_bot.states.body import WeightStates


router = Router()

MIN_WEIGHT = 20.0
MAX_WEIGHT = 400.0


def _parse_weight(text: str) -> float | None:
    match = re.search(r"\d+(?:[.,]\d+)?", text or "")
    if not match:
        return None
    value = float(match.group().replace(",", "."))
    if not (MIN_WEIGHT <= value <= MAX_WEIGHT):
        return None
    return round(value, 1)


@router.message(button(WEIGHT))
async def weight(message: Message, state: FSMContext) -> None:
    await state.clear()
    if not is_authenticated(message.from_user.id):
        await message.answer(
            t("body.login_first"),
            reply_markup=main_menu(authenticated=False),
        )
        return
    try:
        data = await asyncio.to_thread(get_api(message.from_user.id).get_weight)
    except NosiFitAPIError as exc:
        await message.answer(str(exc))
        return

    current = data.get("weight")
    bmi = data.get("bmi")
    lines = [t("weight.title"), ""]
    if current:
        lines.append(
            t("weight.current", weight=f"{float(current):.1f}")
            + (t("weight.bmi", bmi=f"{float(bmi):.1f}") if bmi else "")
        )
    else:
        lines.append(t("weight.none"))
    lines.extend(["", t("weight.prompt")])
    await state.set_state(WeightStates.entering_weight)
    await message.answer("\n".join(lines), reply_markup=cancel_keyboard("weight"))


@router.message(WeightStates.entering_weight)
async def enter_weight(message: Message, state: FSMContext) -> None:
    value = _parse_weight(message.text or "")
    if value is None:
        await message.answer(
            t("weight.invalid"),
            reply_markup=cancel_keyboard("weight"),
        )
        return
    try:
        await asyncio.to_thread(get_api(message.from_user.id).update_weight, value)
    except NosiFitAPIError as exc:
        await message.answer(str(exc))
        return
    await state.clear()
    await message.answer(
        t("weight.updated", weight=f"{value:.1f}"),
        reply_markup=nutrition_mode_menu(),
    )


@router.callback_query(F.data == "weight:cancel")
async def cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    try:
        await callback.message.edit_text(t("common.cancelled"))
    except TelegramBadRequest:
        pass
