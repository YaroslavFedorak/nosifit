from telegram import Update
from telegram.ext import ContextTypes

from telegram_bot.keyboards.main import main_menu


async def water(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return

    await update.message.reply_text(
        "💧 Вода\n\n"
        "Введення води підключимо наступним етапом.",
        reply_markup=main_menu(),
    )
