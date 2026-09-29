from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from telegram_bot.keyboards.main import main_menu

router = Router()

WELCOME_TEXT = (
    "NosiFit

"
    "Швидко додавай дані про свій день — аналіз залишаємо вебзастосунку.

"
    "Оберіть, що хочете додати:"
)

@router.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer(WELCOME_TEXT, reply_markup=main_menu())

@router.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer(
        "Оберіть потрібний розділ у меню.

"
        "/start — відкрити головне меню
"
        "/help — показати цю підказку
"
        "/cancel — скасувати поточну дію",
        reply_markup=main_menu(),
    )