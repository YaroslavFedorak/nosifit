from aiogram import Bot, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import ChatMemberUpdated, Message

from telegram_bot.handlers.auth import HELP_TEXT, do_connect
from telegram_bot.keyboards.auth import auth_menu
from telegram_bot.keyboards.main import main_menu
from telegram_bot.runtime import is_authenticated
from telegram_bot.security import start_throttle


router = Router()


WELCOME_TEXT = (
    "👋 <b>Ласкаво просимо до NosiFit</b>\n\n"
    "Швидко додавай дані про свій день — "
    "аналіз залишаємо вебзастосунку."
)


@router.message(CommandStart())
async def start(message: Message, state: FSMContext, command: CommandObject) -> None:
    if not start_throttle.allow(message.from_user.id):
        return
    await state.clear()

    # t.me/<bot>?start=connect from the profile page's "Connect Telegram".
    if (command.args or "").strip() == "connect" and not is_authenticated(message.from_user.id):
        await do_connect(message, state)
        return

    if not is_authenticated(message.from_user.id):
        await message.answer(WELCOME_TEXT, reply_markup=main_menu(authenticated=False))
        await message.answer("Оберіть дію:", reply_markup=auth_menu())
        return

    await message.answer(
        WELCOME_TEXT + "\n\nОберіть, що хочете додати:",
        reply_markup=main_menu(authenticated=True),
    )


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    if not is_authenticated(message.from_user.id):
        await message.answer(HELP_TEXT, reply_markup=auth_menu())
        return

    await message.answer(
        "Оберіть потрібний розділ у меню.\n\n"
        "/start — відкрити головне меню\n"
        "/help — показати цю підказку\n"
        "/logout — вийти з NosiFit\n"
        "/cancel — скасувати поточну дію\n\n"
        "Відключити Telegram від акаунта: сайт → Профіль → Підключені акаунти.",
        reply_markup=main_menu(authenticated=True),
    )


@router.my_chat_member()
async def left_alone_in_groups(event: ChatMemberUpdated, bot: Bot) -> None:
    """Added to a group or channel: leave. The bot serves private chats only."""
    if event.chat.type == "private":
        return
    if event.new_chat_member.status in ("member", "administrator"):
        try:
            await bot.leave_chat(event.chat.id)
        except Exception:
            pass
