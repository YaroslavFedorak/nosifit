import asyncio
import html
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from telegram_bot.keyboards.auth import auth_menu
from telegram_bot.keyboards.main import LOGIN, LOGOUT, main_menu
from telegram_bot.runtime import authenticate, logout
from telegram_bot.security import login_throttle
from telegram_bot.services.api import NosiFitAPIError
from telegram_bot.states.auth import AuthStates


router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "auth:login")
async def login_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(AuthStates.entering_email)
    await callback.message.edit_text(
        "🔐 <b>Вхід у NosiFit</b>\n\n"
        "Введіть email, який використовуєте на сайті NosiFit:"
    )


@router.message(F.text == LOGIN)
async def login_button(message: Message, state: FSMContext) -> None:
    await state.set_state(AuthStates.entering_email)
    await message.answer(
        "🔐 <b>Вхід у NosiFit</b>\n\n"
        "Введіть email, який використовуєте на сайті NosiFit:"
    )


@router.message(Command("login"))
async def login_command(message: Message, state: FSMContext) -> None:
    await state.set_state(AuthStates.entering_email)
    await message.answer(
        "🔐 <b>Вхід у NosiFit</b>\n\n"
        "Введіть email, який використовуєте на сайті NosiFit:"
    )


@router.message(AuthStates.entering_email)
async def enter_email(message: Message, state: FSMContext) -> None:
    email = (message.text or "").strip().lower()
    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        await message.answer("Введіть коректний email.")
        return

    await state.update_data(email=email)
    await state.set_state(AuthStates.entering_password)
    await message.answer(
        "Введіть пароль від вашого акаунта NosiFit.\n\n"
        "Пароль використовується лише для входу та не зберігається після авторизації."
    )


@router.message(AuthStates.entering_password)
async def enter_password(message: Message, state: FSMContext) -> None:
    password = message.text or ""
    try:
        await message.delete()
    except Exception:
        pass

    if not password:
        await message.answer("Пароль не може бути порожнім.")
        return

    data = await state.get_data()
    email = data.get("email", "")

    if not login_throttle.allow(message.from_user.id):
        await state.clear()
        await message.answer(
            "❌ Забагато спроб входу. Спробуйте через 15 хвилин.",
            reply_markup=auth_menu(),
        )
        return

    try:
        await asyncio.to_thread(
            authenticate,
            message.from_user.id,
            email,
            password,
        )
    except NosiFitAPIError as exc:
        await state.clear()
        await message.answer(
            f"❌ {html.escape(str(exc))}\n\nСпробуйте ще раз:",
            reply_markup=auth_menu(),
        )
        return
    except Exception:
        # Internal details (URLs, library errors) stay out of the chat.
        logger.exception("Bot login failed")
        await state.clear()
        await message.answer(
            "❌ Не вдалося увійти. Спробуйте пізніше.",
            reply_markup=auth_menu(),
        )
        return

    login_throttle.reset(message.from_user.id)

    await state.clear()
    await message.answer(
        "✅ <b>Ви успішно авторизувалися в NosiFit.</b>\n\n"
        "Тепер Telegram-бот працює з вашим акаунтом NosiFit.",
        reply_markup=main_menu(authenticated=True),
    )


@router.message(F.text == LOGOUT)
async def logout_button(message: Message, state: FSMContext) -> None:
    logout(message.from_user.id)
    await state.clear()
    await message.answer(
        "Ви вийшли з акаунта NosiFit.",
        reply_markup=main_menu(authenticated=False),
    )


@router.message(Command("logout"))
async def logout_command(message: Message, state: FSMContext) -> None:
    logout(message.from_user.id)
    await state.clear()
    await message.answer(
        "Ви вийшли з акаунта NosiFit.",
        reply_markup=main_menu(authenticated=False),
    )
