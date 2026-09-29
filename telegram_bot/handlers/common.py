from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from telegram_bot.keyboards.main import main_menu


router = Router()


@router.message(Command("cancel"))
async def cancel(message: Message) -> None:
    await message.answer(
        "Дію скасовано.",
        reply_markup=main_menu(),
    )


@router.message()
async def unknown(message: Message) -> None:
    await message.answer(
        "Оберіть дію через кнопки нижче або введіть /help.",
        reply_markup=main_menu(),
    )
