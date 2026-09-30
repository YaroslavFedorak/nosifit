from aiogram import F, Router
from aiogram.types import Message

from telegram_bot.keyboards.main import WATER, main_menu
from telegram_bot.runtime import is_authenticated


router = Router()


@router.message(F.text == WATER)
async def water(message: Message) -> None:
    await message.answer(
        "💧 Вода\n\n"
        "Введення води підключимо наступним етапом.",
        reply_markup=main_menu(authenticated=is_authenticated(message.from_user.id)),
    )
