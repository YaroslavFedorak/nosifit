from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

NUTRITION = "🍽 Харчування"
WATER = "💧 Вода"
WEIGHT = "⚖️ Вага"

def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=NUTRITION)],
            [KeyboardButton(text=WATER), KeyboardButton(text=WEIGHT)],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Оберіть дію",
    )