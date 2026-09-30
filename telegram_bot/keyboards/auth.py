from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def auth_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔐 Увійти в NosiFit",
                    callback_data="auth:login",
                )
            ]
        ]
    )
