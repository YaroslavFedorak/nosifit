from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

LOGIN_CB = "auth:login"
REGISTER_CB = "auth:register"
CONNECT_CB = "auth:connect"
HELP_CB = "auth:help"
RESEND_CB = "auth:resend"


def auth_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔐 Увійти", callback_data=LOGIN_CB)],
            [InlineKeyboardButton(text="✨ Створити акаунт", callback_data=REGISTER_CB)],
            [InlineKeyboardButton(text="🔗 Підключити акаунт", callback_data=CONNECT_CB)],
            [InlineKeyboardButton(text="❓ Допомога", callback_data=HELP_CB)],
        ]
    )


def not_linked_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✨ Створити акаунт", callback_data=REGISTER_CB)],
            [InlineKeyboardButton(text="🔗 Підключити наявний акаунт", callback_data=CONNECT_CB)],
        ]
    )


def code_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📨 Надіслати код ще раз", callback_data=RESEND_CB)],
        ]
    )


def retry_login_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔐 Увійти", callback_data=LOGIN_CB)]]
    )


def link_menu(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🌐 Відкрити NosiFit", url=url)]]
    )
