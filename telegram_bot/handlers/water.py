from aiogram import F, Router
from aiogram.types import Message
from telegram_bot.keyboards.main import WATER, main_menu

router = Router()

@router.message(F.text == WATER)
async def water(message: Message) -> None:
    await message.answer("💧 Вода

Введення води підключимо наступним етапом.", reply_markup=main_menu())