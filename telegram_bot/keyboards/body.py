from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from telegram_bot.i18n import t


WATER_PRESETS = ("0.25", "0.33", "0.5", "1")


def water_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"+{value} {t('unit.l')}", callback_data=f"water:add:{value}")
                for value in WATER_PRESETS
            ],
            [
                InlineKeyboardButton(text=t("btn.other_amount"), callback_data="water:custom"),
                InlineKeyboardButton(text=f"− 0.25 {t('unit.l')}", callback_data="water:add:-0.25"),
            ],
        ]
    )


def cancel_keyboard(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("btn.cancel"), callback_data=f"{prefix}:cancel")]
        ]
    )
