from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


WATER_PRESETS = ("0.25", "0.33", "0.5", "1")


def water_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"+{value} л", callback_data=f"water:add:{value}")
                for value in WATER_PRESETS
            ],
            [
                InlineKeyboardButton(text="✏️ Інша кількість", callback_data="water:custom"),
                InlineKeyboardButton(text="− 0.25 л", callback_data="water:add:-0.25"),
            ],
        ]
    )


def cancel_keyboard(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✕ Скасувати", callback_data=f"{prefix}:cancel")]
        ]
    )
