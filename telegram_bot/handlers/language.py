"""/language and the 🌐 button: pick the language of the bot."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from telegram_bot import i18n
from telegram_bot.i18n import t
from telegram_bot.keyboards.main import LANGUAGE, button, main_menu
from telegram_bot.runtime import is_authenticated

router = Router()

LANGUAGE_CB = "lang"


def language_menu() -> InlineKeyboardMarkup:
    current = i18n.current_language()
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=("✅ " if code == current else "") + name,
                    callback_data=f"{LANGUAGE_CB}:{code}",
                )
            ]
            for code, name in i18n.LANGUAGES.items()
        ]
    )


@router.message(Command("language"))
@router.message(button(LANGUAGE))
async def choose_language(message: Message) -> None:
    await message.answer(t("lang.choose"), reply_markup=language_menu())


@router.callback_query(F.data.startswith(f"{LANGUAGE_CB}:"))
async def set_language(callback: CallbackQuery) -> None:
    language = callback.data.split(":", 1)[1]
    if language not in i18n.LANGUAGES:
        await callback.answer()
        return
    i18n.set_language(callback.from_user.id, language)
    await callback.answer()
    # The reply keyboard cannot be edited: send it again in the new language.
    await callback.message.answer(
        t("lang.changed"),
        reply_markup=main_menu(authenticated=is_authenticated(callback.from_user.id)),
    )
    try:
        await callback.message.edit_reply_markup(reply_markup=language_menu())
    except Exception:
        pass
