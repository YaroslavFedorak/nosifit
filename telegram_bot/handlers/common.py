from telegram import Update
from telegram.ext import ContextTypes

from telegram_bot.keyboards.main import main_menu


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return

    context.user_data.clear()
    await update.message.reply_text(
        "Дію скасовано.",
        reply_markup=main_menu(),
    )


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return

    await update.message.reply_text(
        "Оберіть дію через кнопки нижче або введіть /help.",
        reply_markup=main_menu(),
    )
