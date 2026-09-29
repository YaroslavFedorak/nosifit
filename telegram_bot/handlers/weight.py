from aiogram import F, Router
from aiogram.types import Message

from telegram_bot.keyboards.main import WEIGHT, main_menu


router = Router()


@router.message(F.text == WEIGHT)
async def weight(message: Message) -> None:
    await message.answer(
        "⚖️ Вага\n\n"
        "Введення ваги підключимо наступним етапом.",
        reply_markup=main_menu(),
    )
