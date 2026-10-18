"""/consent: accept the privacy policy and health-data processing in the bot.

The web app answers every other request with "consent_required" until the
account has both consents (auth/consent.py); the bot then points here. Both
consents are asked for explicitly, with the policy link, and sent together.
"""

import asyncio

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from telegram_bot.i18n import t
from telegram_bot.keyboards.main import main_menu
from telegram_bot.runtime import get_api, get_config, is_authenticated
from telegram_bot.services.api import NosiFitAPIError

router = Router()

ACCEPT = "consent:accept"
WITHDRAW = "consent:withdraw"


def _site() -> str:
    return get_config().nosi_fit_base_url.rstrip("/")


def consent_text() -> str:
    policy_url = f"{get_config().nosi_fit_base_url.rstrip('/')}/privacy"
    return t("consent.text", policy_url=policy_url)


def consent_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t("consent.btn.accept"), callback_data=ACCEPT)]]
    )


@router.message(Command("consent"))
async def consent_command(message: Message) -> None:
    if not is_authenticated(message.from_user.id):
        await message.answer(t("err.login_first"), reply_markup=main_menu(authenticated=False))
        return
    await message.answer(
        consent_text(), reply_markup=consent_keyboard(), disable_web_page_preview=True
    )


@router.callback_query(F.data == ACCEPT)
async def accept(callback: CallbackQuery) -> None:
    await callback.answer()
    user_id = callback.from_user.id
    if not is_authenticated(user_id):
        await callback.message.answer(t("err.login_first"), reply_markup=main_menu(authenticated=False))
        return
    try:
        await asyncio.to_thread(get_api(user_id).give_consent)
    except NosiFitAPIError as exc:
        await callback.message.answer(str(exc))
        return
    await callback.message.answer(
        t("consent.saved"),
        reply_markup=main_menu(authenticated=True),
    )


def mydata_text() -> str:
    return t("consent.mydata", site=_site())


@router.message(Command("mydata"))
async def mydata_command(message: Message) -> None:
    await message.answer(mydata_text(), disable_web_page_preview=True)


@router.message(Command("withdraw"))
async def withdraw_command(message: Message) -> None:
    if not is_authenticated(message.from_user.id):
        await message.answer(t("err.login_first"), reply_markup=main_menu(authenticated=False))
        return
    await message.answer(
        t("consent.withdraw_prompt"),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=t("consent.btn.withdraw"), callback_data=WITHDRAW)]]
        ),
    )


@router.callback_query(F.data == WITHDRAW)
async def withdraw(callback: CallbackQuery) -> None:
    await callback.answer()
    user_id = callback.from_user.id
    if not is_authenticated(user_id):
        await callback.message.answer(t("err.login_first"), reply_markup=main_menu(authenticated=False))
        return
    try:
        await asyncio.to_thread(get_api(user_id).withdraw_consent)
    except NosiFitAPIError as exc:
        await callback.message.answer(str(exc))
        return
    await callback.message.answer(
        t("consent.withdrawn")
    )
