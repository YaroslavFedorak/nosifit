from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

LOGIN_CB = "auth:login"
REGISTER_CB = "auth:register"
CONNECT_CB = "auth:connect"
HELP_CB = "auth:help"
RESEND_CB = "auth:resend"

# How the user signs in on the website; the link opens that sign-in directly.
CONNECT_VIA = {
    "google": ("🔵 Увійти через Google", "Google"),
    "github": ("⚫ Увійти через GitHub", "GitHub"),
    "password": ("✉️ Увійти з email і паролем", "email і пароль"),
}
CONNECT_VIA_CB = {via: f"{CONNECT_CB}:{via}" for via in CONNECT_VIA}


def auth_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔐 Увійти", callback_data=LOGIN_CB)],
            [InlineKeyboardButton(text="✨ Створити новий акаунт", callback_data=REGISTER_CB)],
            [InlineKeyboardButton(text="❓ Допомога", callback_data=HELP_CB)],
        ]
    )


def connect_menu() -> InlineKeyboardMarkup:
    """"How do you sign in to NosiFit?" — one button per sign-in method."""
    rows = [
        [InlineKeyboardButton(text=label, callback_data=CONNECT_VIA_CB[via])]
        for via, (label, _) in CONNECT_VIA.items()
    ]
    rows.append(
        [InlineKeyboardButton(text="✨ У мене немає акаунта — створити", callback_data=REGISTER_CB)]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


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


def link_menu(url: str, via: str) -> InlineKeyboardMarkup:
    label = CONNECT_VIA.get(via, ("🌐 Відкрити NosiFit", ""))[0]
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=label, url=url)]])
