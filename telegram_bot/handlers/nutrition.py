from telegram import Update
from telegram.ext import ContextTypes

from telegram_bot.keyboards.main import main_menu


async def nutrition(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return

    await update.message.reply_text(
        "🍽 Харчування\n\n"
        "Введення харчування підключимо наступним етапом.",
        reply_markup=main_menu(),
    )
