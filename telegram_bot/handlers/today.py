"""The Today card: one message with an HTML widget that shows the day and logs
water and habits with one tap.

Taps in the card arrive as ``widget_query`` updates, which aiogram 3.31 does
not know: WidgetQueryMiddleware takes them before aiogram drops them. The
card asks for fresh state each time it comes on screen ("r"), so a day
changed on the website shows up without resending the message.
"""

import asyncio
import json
import logging
import re
from collections import OrderedDict

from aiogram import BaseMiddleware, Bot, F, Router
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, Update

from telegram_bot import i18n
from telegram_bot.handlers.training import start_add_exercise
from telegram_bot.handlers.weight import ask_weight
from telegram_bot.i18n import t
from telegram_bot.keyboards.main import TODAY, button, main_menu
from telegram_bot.runtime import get_api, is_authenticated, local_now, restore
from telegram_bot.services.api import NosiFitAPI, NosiFitAPIError
from telegram_bot.services.widget_api import AnswerWidgetQuery, EditMessageWidgetData, SendWidget
from telegram_bot.widgets.render import today_html
from telegram_bot.widgets.state import build_state, day_caption

logger = logging.getLogger(__name__)
router = Router()

WATER = {"w250": 0.25, "w500": 0.5}
HABIT = re.compile(r"h(\d{1,9})")

# What each card last showed, without its revision: an edit that changes
# nothing is skipped (it would count against the bot's sending limits).
_shown: OrderedDict[tuple[int, int], str] = OrderedDict()
SHOWN_LIMIT = 5000


def _content(state: str) -> str:
    data = json.loads(state)
    data.pop("r", None)
    return json.dumps(data, sort_keys=True, ensure_ascii=False)


def _remember(key: tuple[int, int], state: str) -> bool:
    """True when the card did not show this yet."""
    content = _content(state)
    if _shown.get(key) == content:
        return False
    _shown[key] = content
    _shown.move_to_end(key)
    while len(_shown) > SHOWN_LIMIT:
        _shown.popitem(last=False)
    return True


def _optional(call, *args):
    """One part of the day: a part the web app cannot give is left out, not the whole card."""
    try:
        return call(*args)
    except NosiFitAPIError as exc:
        if exc.code == "session_expired":
            raise
        return None


def day_state(api: NosiFitAPI) -> str:
    """Blocking: five reads from the web app."""
    return build_state(
        day=_optional(api.get_day),
        snapshot=_optional(api.get_snapshot),
        habits=_optional(api.get_habits) or [],
        session=_optional(api.get_today_session),
        stats=_optional(api.get_stats, 7),
        now=local_now(),
    )


def _step(state: str) -> str | None:
    try:
        return json.loads(state).get("a")
    except ValueError:
        return None


def card_keyboard(step: str | None = None) -> InlineKeyboardMarkup:
    """The step's own action first (log sleep in the morning, add the meal of the hour), then the rest."""
    def button_(key: str, data: str) -> InlineKeyboardButton:
        return InlineKeyboardButton(text=t(key), callback_data=data)

    if step == "sleep":
        first = button_("w.btn.sleep", "sl:s")
    elif step in ("breakfast", "lunch", "dinner"):
        first = button_(f"w.btn.{step}", f"qf:m:{step}")
    else:
        first = button_("w.btn.food", "qf:m:auto")
    rest = [button_("w.btn.workout", "today:workout"), button_("w.btn.weight", "today:weight")]
    if step == "sleep":
        rest.insert(0, button_("w.btn.food", "qf:m:auto"))
    return InlineKeyboardMarkup(inline_keyboard=[[first], rest])


# The newest card of each chat and the step its buttons were made for. Only
# that card is kept: a new one replaces it, so the chat holds one live card.
_cards: dict[int, tuple[int, str | None]] = {}


async def send_today(bot: Bot, chat_id: int, user_id: int) -> None:
    try:
        state = await asyncio.to_thread(day_state, get_api(user_id))
    except NosiFitAPIError as exc:
        await bot.send_message(chat_id, str(exc))
        return
    try:
        sent = await bot(
            SendWidget(
                chat_id=chat_id,
                html=today_html(i18n.current_language()),
                chat_data=state,
                caption=day_caption(local_now().date()),
                allow_queries=True,
                reply_markup=card_keyboard(_step(state)),
            )
        )
    except TelegramAPIError as exc:
        # The rest of the bot works without the card.
        logger.warning("Today card was not sent: %s", exc)
        return
    if not isinstance(sent, Message):
        return
    _remember((chat_id, sent.message_id), state)
    previous = _cards.get(chat_id)
    _cards[chat_id] = (sent.message_id, _step(state))
    if previous and previous[0] != sent.message_id:
        try:
            await bot.delete_message(chat_id, previous[0])
        except TelegramAPIError:
            # Older than 48 hours or already deleted: Telegram keeps it.
            pass


async def _update_card(bot: Bot, chat_id: int, message_id: int, state: str) -> None:
    """Redraw a card from new state; its buttons follow when the step changed."""
    if _remember((chat_id, message_id), state):
        try:
            await bot(EditMessageWidgetData(chat_id=chat_id, message_id=message_id, chat_data=state))
        except TelegramBadRequest as exc:
            if "not modified" not in str(exc).lower():
                logger.warning("Today card edit failed: %s", exc)
    card = _cards.get(chat_id)
    step = _step(state)
    if card and card[0] == message_id and card[1] != step:
        _cards[chat_id] = (message_id, step)
        try:
            await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=card_keyboard(step))
        except TelegramAPIError as exc:
            logger.warning("Today card buttons were not updated: %s", exc)


async def refresh_card(bot: Bot, chat_id: int, user_id: int) -> None:
    """After an entry made outside the card: show it in the chat's card at once."""
    card = _cards.get(chat_id)
    if card is None:
        return
    try:
        state = await asyncio.to_thread(day_state, get_api(user_id))
    except NosiFitAPIError:
        return
    await _update_card(bot, chat_id, card[0], state)


@router.message(button(TODAY))
@router.message(Command("today"))
async def today(message: Message, state: FSMContext) -> None:
    await state.clear()
    if not is_authenticated(message.from_user.id):
        await message.answer(t("err.login_start"), reply_markup=main_menu(authenticated=False))
        return
    await send_today(message.bot, message.chat.id, message.from_user.id)


@router.callback_query(F.data == "today:workout")
async def card_workout(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await start_add_exercise(callback.message, state, callback.from_user.id)


@router.callback_query(F.data == "today:weight")
async def card_weight(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await ask_weight(callback.message, state, callback.from_user.id)


def _apply(api: NosiFitAPI, data: str) -> None:
    """Blocking: the change a tap asks for. Unknown data changes nothing."""
    if data in WATER:
        api.add_water(WATER[data])
        return
    match = HABIT.fullmatch(data)
    if match:
        habit_id = int(match.group(1))
        habit = next((h for h in api.get_habits() if h.get("user_habit_id") == habit_id), None)
        if habit is None:
            raise NosiFitAPIError(t("err.generic"))
        api.set_habit(habit_id, not habit.get("completed"))


async def answer_widget_query(bot: Bot, query: dict) -> None:
    sender = query.get("from") or {}
    chat = query.get("chat") or {}
    user_id, chat_id, message_id = sender.get("id"), chat.get("id"), query.get("message_id")
    data = str(query.get("data") or "")
    if not (
        isinstance(user_id, int)
        and user_id > 0
        and not sender.get("is_bot")
        and chat.get("type") == "private"
        and chat_id == user_id
        and isinstance(message_id, int)
    ):
        # Only the user's own card in the private chat; the bot never sends it elsewhere.
        await bot(AnswerWidgetQuery(widget_query_id=str(query.get("id"))))
        return

    token = i18n.use_language(user_id, sender.get("language_code"))
    try:
        api = await asyncio.to_thread(restore, user_id)
        state = None
        if api is not None:
            try:
                await asyncio.to_thread(_apply, api, data)
                state = await asyncio.to_thread(day_state, api)
            except NosiFitAPIError:
                state = None
        # A tap that failed gets no state: the card shows its error line.
        await bot(AnswerWidgetQuery(widget_query_id=str(query["id"]), data=state))
        if state:
            await _update_card(bot, chat_id, message_id, state)
    finally:
        i18n.reset_language(token)


class WidgetQueryMiddleware(BaseMiddleware):
    """Outer middleware of dispatcher.update: answers widget queries itself."""

    async def __call__(self, handler, event, data):
        query = (getattr(event, "model_extra", None) or {}).get("widget_query") if isinstance(event, Update) else None
        if not isinstance(query, dict):
            return await handler(event, data)
        try:
            await answer_widget_query(data["bot"], query)
        except TelegramAPIError as exc:
            logger.warning("Widget query failed: %s", exc)
        return None
