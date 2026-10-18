from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from telegram_bot.i18n import t
from telegram_bot.keyboards.main import main_menu
from telegram_bot.runtime import is_authenticated


router = Router()


@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        t("common.cancelled"),
        reply_markup=main_menu(authenticated=is_authenticated(message.from_user.id)),
    )


@router.message()
async def unknown(message: Message) -> None:
    await message.answer(
        t("common.unknown"),
        reply_markup=main_menu(authenticated=is_authenticated(message.from_user.id)),
    )
