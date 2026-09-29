from aiogram import F, Router
from aiogram.types import Message
from telegram_bot.keyboards.main import NUTRITION, main_menu

router = Router()

@router.message(F.text == NUTRITION)
async def nutrition(message: Message) -> None:
    await message.answer("🍽 Харчування

Введення харчування підключимо наступним етапом.", reply_markup=main_menu())