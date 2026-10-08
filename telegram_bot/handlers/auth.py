"""Sign-in, account creation and account connection in the bot.

The Telegram user is identified only by the numeric id from the update
(``from_user.id``). The bot never asks for a NosiFit password:

- Log in: the web app looks up the Telegram identity and opens a session.
- Create account: email -> code from the email -> new account + identity.
- Connect account: a one-time link the user opens in the browser where they
  are signed in to NosiFit, and confirms there.

Error texts are generic; internal details stay in the logs (never codes,
emails or links).
"""

import asyncio
import logging
import re

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, LinkPreviewOptions, Message

from telegram_bot import runtime
from telegram_bot.keyboards.auth import (
    CONNECT_CB,
    CONNECT_VIA,
    CONNECT_VIA_CB,
    HELP_CB,
    LOGIN_CB,
    REGISTER_CB,
    RESEND_CB,
    auth_menu,
    code_menu,
    connect_menu,
    link_menu,
    retry_login_menu,
)
from telegram_bot.keyboards.main import LOGIN, LOGOUT, main_menu
from telegram_bot.security import (
    code_throttle,
    link_throttle,
    login_throttle,
    register_throttle,
)
from telegram_bot.services.telegram_auth import TelegramAuthError, TelegramUser
from telegram_bot.states.auth import RegisterStates

router = Router()
logger = logging.getLogger(__name__)

EMAIL_MAX_LENGTH = 120
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_CODE_RE = re.compile(r"^\d{6}$")
MAX_CODE_TRIES = 5

GENERIC_ERROR = "❌ Щось пішло не так. Спробуйте ще раз трохи пізніше."
RATE_LIMITED = "⏳ Забагато спроб. Спробуйте трохи пізніше."
ALREADY_LINKED = (
    "Цей Telegram уже підключено до акаунта NosiFit. Натисніть «🔐 Увійти»."
)

HELP_TEXT = (
    "<b>NosiFit у Telegram</b>\n\n"
    "🔐 <b>Увійти</b>. Першого разу бот запитає, як ви входите на сайт "
    "NosiFit — через Google, GitHub чи email і пароль — і дасть посилання. "
    "Увійдіть у браузері звичним способом і натисніть «Підключити». Далі "
    "«Увійти» в боті спрацьовує одним натиском.\n"
    "✨ <b>Створити новий акаунт</b> — потрібен лише email і код із листа.\n\n"
    "Бот ніколи не просить пароль: вхід через Google, GitHub чи пароль "
    "відбувається лише на сайті NosiFit у браузері.\n"
    "Відключити Telegram: сайт → Профіль → Підключені акаунти.\n\n"
    "/start — меню\n/login — увійти\n/register — створити акаунт\n"
    "/logout — вийти\n/cancel — скасувати дію"
)

CHOOSE_METHOD_TEXT = (
    "Як ви входите на сайт NosiFit?\n\n"
    "Оберіть свій спосіб: бот дасть посилання, ви увійдете в браузері й "
    "підтвердите. Це потрібно лише один раз."
)


def _tg_user(event) -> TelegramUser:
    return TelegramUser.from_aiogram(event.from_user)


async def _answer(event, text: str, **kwargs) -> None:
    message = event.message if isinstance(event, CallbackQuery) else event
    await message.answer(text, **kwargs)


async def _ack(event) -> None:
    if isinstance(event, CallbackQuery):
        await event.answer()


# --- Log in -----------------------------------------------------------------------------


async def do_login(event, state: FSMContext) -> None:
    await _ack(event)
    await state.clear()
    user = _tg_user(event)

    if not login_throttle.allow(user.id):
        await _answer(event, RATE_LIMITED)
        return

    try:
        await asyncio.to_thread(runtime.login, user)
    except TelegramAuthError as exc:
        if exc.code == "not_linked":
            await _answer(
                event,
                "Цей Telegram ще не підключено до акаунта NosiFit.\n\n"
                + CHOOSE_METHOD_TEXT,
                reply_markup=connect_menu(),
            )
        elif exc.code == "rate_limited":
            await _answer(event, RATE_LIMITED)
        else:
            logger.warning("Telegram login failed: %s", exc.code)
            await _answer(event, GENERIC_ERROR, reply_markup=retry_login_menu())
        return
    except Exception:
        logger.exception("Telegram login failed")
        await _answer(event, GENERIC_ERROR, reply_markup=retry_login_menu())
        return

    login_throttle.reset(user.id)
    await _answer(
        event,
        "✅ Ви увійшли в NosiFit.",
        reply_markup=main_menu(authenticated=True),
    )


@router.callback_query(F.data == LOGIN_CB)
async def login_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await do_login(callback, state)


@router.message(F.text == LOGIN)
async def login_button(message: Message, state: FSMContext) -> None:
    await do_login(message, state)


@router.message(Command("login"))
async def login_command(message: Message, state: FSMContext) -> None:
    await do_login(message, state)


# --- Log out ----------------------------------------------------------------------------


@router.message(F.text == LOGOUT)
async def logout_button(message: Message, state: FSMContext) -> None:
    await logout_command(message, state)


@router.message(Command("logout"))
async def logout_command(message: Message, state: FSMContext) -> None:
    runtime.logout(message.from_user.id)
    await state.clear()
    await message.answer(
        "Ви вийшли з NosiFit у цьому боті.",
        reply_markup=main_menu(authenticated=False),
    )
    await message.answer("Що далі?", reply_markup=auth_menu())


# --- Help -------------------------------------------------------------------------------


@router.callback_query(F.data == HELP_CB)
async def help_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(HELP_TEXT, reply_markup=auth_menu())


# --- Create an account ------------------------------------------------------------------


async def start_registration(event, state: FSMContext) -> None:
    await _ack(event)
    await state.clear()
    if runtime.is_authenticated(event.from_user.id):
        await _answer(event, "Ви вже увійшли в NosiFit.", reply_markup=main_menu(authenticated=True))
        return
    await state.set_state(RegisterStates.entering_email)
    await _answer(
        event,
        "✨ <b>Новий акаунт NosiFit</b>\n\n"
        "Введіть email. На нього прийде код підтвердження.\n"
        "Пароль не потрібен. /cancel — скасувати.",
    )


@router.callback_query(F.data == REGISTER_CB)
async def register_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await start_registration(callback, state)


@router.message(Command("register"))
async def register_command(message: Message, state: FSMContext) -> None:
    await start_registration(message, state)


async def _send_code(event, state: FSMContext, email: str) -> None:
    user = _tg_user(event)
    if not register_throttle.allow(user.id):
        await state.clear()
        await _answer(event, RATE_LIMITED, reply_markup=auth_menu())
        return

    try:
        await asyncio.to_thread(runtime.register_start, user, email)
    except TelegramAuthError as exc:
        if exc.code == "invalid_email":
            await _answer(event, "Введіть коректний email.")
            return
        await state.clear()
        if exc.code == "already_linked":
            await _answer(event, ALREADY_LINKED, reply_markup=retry_login_menu())
        elif exc.code == "rate_limited":
            await _answer(event, RATE_LIMITED, reply_markup=auth_menu())
        else:
            logger.warning("Telegram registration start failed: %s", exc.code)
            await _answer(event, GENERIC_ERROR, reply_markup=auth_menu())
        return
    except Exception:
        logger.exception("Telegram registration start failed")
        await state.clear()
        await _answer(event, GENERIC_ERROR, reply_markup=auth_menu())
        return

    await state.update_data(email=email, tries=0)
    await state.set_state(RegisterStates.entering_code)
    # The same text whether or not the address already has an account.
    await _answer(
        event,
        "📨 Ми надіслали лист на вказану адресу.\n\n"
        "• Якщо там 6-значний код — введіть його тут.\n"
        "• Якщо з цією адресою вже є акаунт NosiFit, код не надсилається: "
        "лист пояснить, як підключити Telegram до наявного акаунта.\n\n"
        "Код дійсний 10 хвилин. /cancel — скасувати.",
        reply_markup=code_menu(),
    )


def _not_a_command(message: Message) -> bool:
    return not (message.text or "").startswith("/")


@router.message(RegisterStates.entering_email, F.text, _not_a_command)
async def enter_email(message: Message, state: FSMContext) -> None:
    email = (message.text or "").strip().lower()
    if len(email) > EMAIL_MAX_LENGTH or not _EMAIL_RE.match(email):
        await message.answer("Введіть коректний email або /cancel.")
        return
    await _send_code(message, state, email)


@router.callback_query(F.data == RESEND_CB)
async def resend_code(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = await state.get_data()
    email = data.get("email")
    if await state.get_state() != RegisterStates.entering_code.state or not email:
        await callback.message.answer(
            "Почніть реєстрацію знову.", reply_markup=auth_menu()
        )
        return
    await _send_code(callback, state, email)


@router.message(RegisterStates.entering_code, F.text, _not_a_command)
async def enter_code(message: Message, state: FSMContext) -> None:
    code = (message.text or "").strip().replace(" ", "")
    # The code is a secret: remove it from the chat history.
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    user = _tg_user(message)
    data = await state.get_data()
    email = data.get("email")
    tries = int(data.get("tries") or 0) + 1

    if not email:
        await state.clear()
        await message.answer("Почніть реєстрацію знову.", reply_markup=auth_menu())
        return

    if not _CODE_RE.match(code):
        await message.answer("Код складається з 6 цифр. Спробуйте ще раз або /cancel.")
        return

    if tries > MAX_CODE_TRIES or not code_throttle.allow(user.id):
        await state.clear()
        await message.answer(
            "Забагато спроб. Почніть реєстрацію знову.", reply_markup=auth_menu()
        )
        return
    await state.update_data(tries=tries)

    try:
        await asyncio.to_thread(runtime.register_verify, user, email, code)
    except TelegramAuthError as exc:
        if exc.code == "invalid_code":
            await message.answer(
                "Код невірний або застарів. Спробуйте ще раз, надішліть новий код "
                "або /cancel.",
                reply_markup=code_menu(),
            )
            return
        await state.clear()
        if exc.code == "already_linked":
            await message.answer(ALREADY_LINKED, reply_markup=retry_login_menu())
        elif exc.code == "email_unavailable":
            await message.answer(
                "Цю адресу не можна використати для нового акаунта. Якщо у вас "
                "уже є акаунт NosiFit, натисніть «🔗 Підключити акаунт».",
                reply_markup=auth_menu(),
            )
        elif exc.code in ("too_many_attempts", "rate_limited"):
            await message.answer(
                "Забагато спроб. Почніть реєстрацію знову трохи пізніше.",
                reply_markup=auth_menu(),
            )
        else:
            logger.warning("Telegram registration verify failed: %s", exc.code)
            await message.answer(GENERIC_ERROR, reply_markup=auth_menu())
        return
    except Exception:
        logger.exception("Telegram registration verify failed")
        await state.clear()
        await message.answer(GENERIC_ERROR, reply_markup=auth_menu())
        return

    await state.clear()
    await message.answer(
        "✅ Ваш акаунт NosiFit створено, ви увійшли.\n\n"
        "Щоб користуватися сайтом, встановіть пароль через «Забули пароль?» "
        "на сторінці входу.",
        reply_markup=main_menu(authenticated=True),
    )


# --- Connect an existing account --------------------------------------------------------


async def choose_method(event, state: FSMContext) -> None:
    await _ack(event)
    await state.clear()
    await _answer(event, CHOOSE_METHOD_TEXT, reply_markup=connect_menu())


async def do_connect(event, state: FSMContext, via: str) -> None:
    await _ack(event)
    await state.clear()
    user = _tg_user(event)

    if via not in CONNECT_VIA:
        await _answer(event, CHOOSE_METHOD_TEXT, reply_markup=connect_menu())
        return

    if not link_throttle.allow(user.id):
        await _answer(event, RATE_LIMITED)
        return

    try:
        url, expires_in = await asyncio.to_thread(runtime.link_url, user, via)
    except TelegramAuthError as exc:
        if exc.code == "already_linked":
            await _answer(event, ALREADY_LINKED, reply_markup=retry_login_menu())
        elif exc.code == "rate_limited":
            await _answer(event, RATE_LIMITED)
        else:
            logger.warning("Telegram link request failed: %s", exc.code)
            await _answer(event, GENERIC_ERROR, reply_markup=auth_menu())
        return
    except Exception:
        logger.exception("Telegram link request failed")
        await _answer(event, GENERIC_ERROR, reply_markup=auth_menu())
        return

    minutes = max(1, expires_in // 60)
    method = CONNECT_VIA[via][1]
    sign_in_step = (
        "2. Увійдіть у NosiFit своїм email і паролем (на сайті, не тут).\n"
        if via == "password"
        else f"2. Увійдіть через {method} — відкриється сторінка {method}.\n"
    )
    text = (
        f"🔗 <b>Вхід через {method}</b>\n\n"
        "1. Натисніть кнопку нижче — відкриється браузер.\n"
        + sign_in_step
        + "3. Перевірте свій акаунт і натисніть «Підключити».\n"
        "4. Поверніться сюди й натисніть «🔐 Увійти».\n\n"
        f"Посилання одноразове й діє {minutes} хв. Нікому його не пересилайте."
    )
    message = event.message if isinstance(event, CallbackQuery) else event
    # protect_content: the link cannot be forwarded or saved from the chat.
    try:
        await message.answer(text, reply_markup=link_menu(url, via), protect_content=True)
    except TelegramBadRequest:
        # Telegram rejects some URLs in buttons (e.g. http://localhost).
        await message.answer(
            f"{text}\n\n{url}",
            protect_content=True,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )


@router.callback_query(F.data.in_(set(CONNECT_VIA_CB.values())))
async def connect_via_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await do_connect(callback, state, callback.data.rsplit(":", 1)[1])


# Buttons in messages sent before the per-method choice existed.
@router.callback_query(F.data == CONNECT_CB)
async def connect_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await choose_method(callback, state)


@router.message(Command("connect"))
async def connect_command(message: Message, state: FSMContext) -> None:
    await choose_method(message, state)
