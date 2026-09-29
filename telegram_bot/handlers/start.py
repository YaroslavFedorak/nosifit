from telegram import Update
from telegram.ext import ContextTypes

from telegram_bot.keyboards.main import main_menu


WELCOME_TEXT = (
    "NosiFit\n\n"
    "Швидко додавай дані про свій день — аналіз залишаємо вебзастосунку.\n\n"
    "Оберіть, що хочете додати:"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return

    await update.message.reply_text(WELCOME_TEXT, reply_markup=main_menu())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return

    await update.message.reply_text(
        "Оберіть потрібний розділ у меню.\n\n"
        "/start — відкрити головне меню\n"
        "/help — показати цю підказку\n"
        "/cancel — скасувати поточну дію",
        reply_markup=main_menu(),
    )
