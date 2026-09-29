from telegram import ReplyKeyboardMarkup

NUTRITION = "🍽 Харчування"
WATER = "💧 Вода"
WEIGHT = "⚖️ Вага"


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[NUTRITION], [WATER, WEIGHT]],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Оберіть дію",
    )
