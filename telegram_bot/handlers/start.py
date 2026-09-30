from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from telegram_bot.keyboards.auth import auth_menu
from telegram_bot.keyboards.main import main_menu
from telegram_bot.runtime import is_authenticated


router = Router()


WELCOME_TEXT = (
    "NosiFit\n\n"
    "Швидко додавай дані про свій день — "
    "аналіз залишаємо вебзастосунку."
)


@router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    await state.clear()

    if not is_authenticated(message.from_user.id):
        await message.answer(
            WELCOME_TEXT + "\n\nСпочатку увійдіть у свій акаунт NosiFit.",
            reply_markup=auth_menu(),
        )
        return

    await message.answer(
        WELCOME_TEXT + "\n\nОберіть, що хочете додати:",
        reply_markup=main_menu(authenticated=True),
    )


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    if not is_authenticated(message.from_user.id):
        await message.answer(
            "Спочатку увійдіть у свій акаунт NosiFit.",
            reply_markup=auth_menu(),
        )
        return

    await message.answer(
        "Оберіть потрібний розділ у меню.\n\n"
        "/start — відкрити головне меню\n"
        "/help — показати цю підказку\n"
        "/login — увійти в NosiFit\n"
        "/logout — вийти з NosiFit\n"
        "/cancel — скасувати поточну дію",
        reply_markup=main_menu(authenticated=True),
    )
