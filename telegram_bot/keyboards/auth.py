from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from telegram_bot.i18n import t

LOGIN_CB = "auth:login"
REGISTER_CB = "auth:register"
CONNECT_CB = "auth:connect"
HELP_CB = "auth:help"
RESEND_CB = "auth:resend"

# How the user signs in on the website; the link opens that sign-in directly.
CONNECT_VIA = ("google", "github", "password")
CONNECT_VIA_CB = {via: f"{CONNECT_CB}:{via}" for via in CONNECT_VIA}


def connect_method(via: str) -> str:
    """Name of the sign-in method inside a sentence."""
    return t("auth.method.password") if via == "password" else {"google": "Google", "github": "GitHub"}[via]


def auth_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("auth.btn.login"), callback_data=LOGIN_CB)],
            [InlineKeyboardButton(text=t("auth.btn.register"), callback_data=REGISTER_CB)],
            [InlineKeyboardButton(text=t("auth.btn.help"), callback_data=HELP_CB)],
        ]
    )


def connect_menu() -> InlineKeyboardMarkup:
    """"How do you sign in to NosiFit?" — one button per sign-in method."""
    rows = [
        [InlineKeyboardButton(text=t(f"auth.btn.{via}"), callback_data=CONNECT_VIA_CB[via])]
        for via in CONNECT_VIA
    ]
    rows.append([InlineKeyboardButton(text=t("auth.btn.no_account"), callback_data=REGISTER_CB)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def code_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("auth.btn.resend"), callback_data=RESEND_CB)],
        ]
    )


def retry_login_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t("auth.btn.login"), callback_data=LOGIN_CB)]]
    )


def link_menu(url: str, via: str) -> InlineKeyboardMarkup:
    label = t(f"auth.btn.{via}") if via in CONNECT_VIA else t("auth.btn.open")
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=label, url=url)]])
