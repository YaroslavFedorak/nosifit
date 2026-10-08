from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

NUTRITION = "🍽 Харчування"
WATER = "💧 Вода"
WEIGHT = "⚖️ Вага"
LOGIN = "🔐 Увійти"
LOGOUT = "🚪 Вийти"


def main_menu(*, authenticated: bool = False) -> ReplyKeyboardMarkup:
    if not authenticated:
        return ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=LOGIN)]],
            resize_keyboard=True,
            is_persistent=True,
            input_field_placeholder="Увійдіть у NosiFit",
        )

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=NUTRITION)],
            [KeyboardButton(text=WATER), KeyboardButton(text=WEIGHT)],
            [KeyboardButton(text=LOGOUT)],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Оберіть дію",
    )
