"""Reply keyboards: the home screen picks a mode, each mode has its own
buttons and "🏠 Home" goes back.

The constants are catalog keys, not texts: a button is shown in the user's
language (``t``) and matched in every language (``button``)."""

from aiogram import F
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from telegram_bot.i18n import t, variants

# Home
TRAINING = "btn.training"
NUTRITION = "btn.nutrition"
LOGIN = "btn.login"
LOGOUT = "btn.logout"
HOME = "btn.home"
LANGUAGE = "btn.language"

# Training mode
ADD_EXERCISE = "btn.add_exercise"
MY_WORKOUT = "btn.my_workout"

# Nutrition mode
FOOD = "btn.food"
WATER = "btn.water"
WEIGHT = "btn.weight"

_BUTTONS = (
    TRAINING, NUTRITION, LOGIN, LOGOUT, HOME, LANGUAGE, ADD_EXERCISE, MY_WORKOUT, FOOD, WATER, WEIGHT
)
MENU_TEXTS = frozenset(text for key in _BUTTONS for text in variants(key))


def button(*keys: str):
    """Filter: the message is one of these buttons, in any language."""
    return F.text.in_({text for key in keys for text in variants(key)})


def _keyboard(rows: list[list[str]], placeholder: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t(key)) for key in row] for row in rows],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder=t(placeholder),
    )


def main_menu(*, authenticated: bool = False) -> ReplyKeyboardMarkup:
    """Home: one button per mode."""
    if not authenticated:
        return _keyboard([[LOGIN, LANGUAGE]], "ph.login")
    return _keyboard([[TRAINING, NUTRITION], [LANGUAGE, LOGOUT]], "ph.section")


def training_menu() -> ReplyKeyboardMarkup:
    return _keyboard([[ADD_EXERCISE, MY_WORKOUT], [HOME]], "ph.exercise")


def nutrition_mode_menu() -> ReplyKeyboardMarkup:
    return _keyboard([[FOOD, WATER, WEIGHT], [HOME]], "ph.action")
