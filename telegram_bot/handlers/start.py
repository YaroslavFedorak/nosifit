from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import ChatMemberUpdated, Message

from telegram_bot.handlers.auth import HELP_TEXT, choose_method
from telegram_bot.keyboards.auth import auth_menu
from telegram_bot.keyboards.main import HOME, main_menu
from telegram_bot.runtime import is_authenticated
from telegram_bot.security import start_throttle


router = Router()


WELCOME_TEXT = (
    "<b>NosiFit</b>\n\n"
    "Тут зручно записувати тренування, їжу, воду й вагу. "
    "Статистика й аналіз — на сайті."
)


@router.message(CommandStart())
async def start(message: Message, state: FSMContext, command: CommandObject) -> None:
    if not start_throttle.allow(message.from_user.id):
        return
    await state.clear()

    # t.me/<bot>?start=connect from the profile page's "Connect Telegram".
    if (command.args or "").strip() == "connect" and not is_authenticated(message.from_user.id):
        await choose_method(message, state)
        return

    if not is_authenticated(message.from_user.id):
        await message.answer(WELCOME_TEXT, reply_markup=main_menu(authenticated=False))
        await message.answer("Оберіть дію:", reply_markup=auth_menu())
        return

    await message.answer(
        WELCOME_TEXT + "\n\nОберіть, що хочете додати:",
        reply_markup=main_menu(authenticated=True),
    )


@router.message(F.text == HOME)
async def home(message: Message, state: FSMContext) -> None:
    """Back to the mode choice from any mode or unfinished step."""
    await state.clear()
    authenticated = is_authenticated(message.from_user.id)
    await message.answer(
        "🏠 Головна" if authenticated else WELCOME_TEXT,
        reply_markup=main_menu(authenticated=authenticated),
    )


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    if not is_authenticated(message.from_user.id):
        await message.answer(HELP_TEXT, reply_markup=auth_menu())
        return

    await message.answer(
        "Основне — у кнопках унизу. Команди:\n\n"
        "/start — головне меню\n"
        "/help — ця підказка\n"
        "/logout — вийти\n"
        "/cancel — скасувати те, що робите зараз\n\n"
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
