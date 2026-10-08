"""Reply keyboards: the home screen picks a mode, each mode has its own
buttons and "🏠 Головна" goes back."""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

# Home
TRAINING = "🏋️ Тренування"
NUTRITION = "🍽 Харчування"
LOGIN = "🔐 Увійти"
LOGOUT = "🚪 Вийти"
HOME = "🏠 Головна"

# Training mode
ADD_EXERCISE = "➕ Додати вправу"
MY_WORKOUT = "📋 Моє тренування"

# Nutrition mode
FOOD = "🍽 Їжа"
WATER = "💧 Вода"
WEIGHT = "⚖️ Вага"

MENU_TEXTS = frozenset(
    {TRAINING, NUTRITION, LOGIN, LOGOUT, HOME, ADD_EXERCISE, MY_WORKOUT, FOOD, WATER, WEIGHT}
)


def _keyboard(rows: list[list[str]], placeholder: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=text) for text in row] for row in rows],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder=placeholder,
    )


def main_menu(*, authenticated: bool = False) -> ReplyKeyboardMarkup:
    """Home: one button per mode."""
    if not authenticated:
        return _keyboard([[LOGIN]], "Увійдіть у NosiFit")
    return _keyboard([[TRAINING, NUTRITION], [LOGOUT]], "Оберіть розділ")


def training_menu() -> ReplyKeyboardMarkup:
    return _keyboard([[ADD_EXERCISE, MY_WORKOUT], [HOME]], "Назва вправи або кнопка")


def nutrition_mode_menu() -> ReplyKeyboardMarkup:
    return _keyboard([[FOOD, WATER, WEIGHT], [HOME]], "Оберіть дію")
