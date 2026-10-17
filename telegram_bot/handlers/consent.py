"""/consent: accept the privacy policy and health-data processing in the bot.

The web app answers every other request with "consent_required" until the
account has both consents (auth/consent.py); the bot then points here. Both
consents are asked for explicitly, with the policy link, and sent together.
"""

import asyncio

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

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
    return (
        "🔒 <b>Згода на обробку даних</b>\n\n"
        f"Перед використанням прочитайте <a href=\"{policy_url}\">політику конфіденційності</a>.\n\n"
        "Натискаючи кнопку нижче, ви:\n"
        "1) підтверджуєте, що вам виповнилося 16 років;\n"
        "2) приймаєте політику конфіденційності;\n"
        "3) надаєте <b>явну згоду</b> на обробку ваших даних про здоров'я "
        "(вага, харчування, тренування, сон, звички) для роботи сервісу та "
        "його агрегованої внутрішньої статистики.\n\n"
        "Відкликати згоду: /withdraw. Отримати свої дані: /mydata."
    )


def consent_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="✅ Мені 16+, приймаю обидві згоди", callback_data=ACCEPT)]]
    )


@router.message(Command("consent"))
async def consent_command(message: Message) -> None:
    if not is_authenticated(message.from_user.id):
        await message.answer("Спочатку увійдіть: /login", reply_markup=main_menu(authenticated=False))
        return
    await message.answer(
        consent_text(), reply_markup=consent_keyboard(), disable_web_page_preview=True
    )


@router.callback_query(F.data == ACCEPT)
async def accept(callback: CallbackQuery) -> None:
    await callback.answer()
    user_id = callback.from_user.id
    if not is_authenticated(user_id):
        await callback.message.answer("Спочатку увійдіть: /login", reply_markup=main_menu(authenticated=False))
        return
    try:
        await asyncio.to_thread(get_api(user_id).give_consent)
    except NosiFitAPIError as exc:
        await callback.message.answer(str(exc))
        return
    await callback.message.answer(
        "✅ Дякуємо! Згоду збережено, можна продовжувати.",
        reply_markup=main_menu(authenticated=True),
    )


def mydata_text() -> str:
    site = _site()
    return (
        "📦 <b>Ваші дані</b>\n\n"
        f"Файл з усіма вашими даними можна завантажити на сайті: {site}/privacy/my-data\n\n"
        "Якщо ви входили лише через Telegram і не маєте пароля:\n"
        f"1) відкрийте {site}/auth/reset і введіть email свого акаунта;\n"
        "2) за посиланням з листа встановіть пароль;\n"
        "3) увійдіть на сайті й відкрийте посилання вище.\n\n"
        "Бот не надсилає файл з даними в чат: так ваші дані не залишаться в історії Telegram."
    )


@router.message(Command("mydata"))
async def mydata_command(message: Message) -> None:
    await message.answer(mydata_text(), disable_web_page_preview=True)


@router.message(Command("withdraw"))
async def withdraw_command(message: Message) -> None:
    if not is_authenticated(message.from_user.id):
        await message.answer("Спочатку увійдіть: /login", reply_markup=main_menu(authenticated=False))
        return
    await message.answer(
        "⚠️ <b>Відкликати згоду на обробку даних про здоров'я?</b>\n\n"
        "Буде одразу видалено: харчування, воду, вагу, тренування, сон, звички, дані профілю "
        "і внутрішню статистику про ваші дії. Обліковий запис і способи входу залишаться.\n"
        "Скасувати видалення неможливо. Зберегти дані перед цим: /mydata",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Відкликати й видалити записи", callback_data=WITHDRAW)]]
        ),
    )


@router.callback_query(F.data == WITHDRAW)
async def withdraw(callback: CallbackQuery) -> None:
    await callback.answer()
    user_id = callback.from_user.id
    if not is_authenticated(user_id):
        await callback.message.answer("Спочатку увійдіть: /login", reply_markup=main_menu(authenticated=False))
        return
    try:
        await asyncio.to_thread(get_api(user_id).withdraw_consent)
    except NosiFitAPIError as exc:
        await callback.message.answer(str(exc))
        return
    await callback.message.answer(
        "Згоду відкликано, записи видалено. Обліковий запис залишився: "
        "щоб знову користуватися NosiFit, надайте згоду: /consent"
    )
