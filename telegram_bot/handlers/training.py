"""🏋️ Тренування: log today's workout while training.

One message is edited in place. Today's workout is the screen everything
returns to; typing an exercise name anywhere in the flow searches, and
while an exercise is open typing "60 10" logs one set. Every change is sent
to the server at once (the whole list, see telegram_bot.services.training),
so nothing is lost if the user never presses "Завершити".

Two taps arriving together are serialised per user; actions that must not
repeat (one more set, deletions) also carry the revision of the screen they
were pressed on.
"""

import asyncio
import copy
import html

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from telegram_bot.keyboards.main import LOGIN, LOGOUT, NUTRITION, TRAINING, WATER, WEIGHT, main_menu
from telegram_bot.keyboards.training import (
    card_keyboard,
    delete_keyboard,
    finish_keyboard,
    home_keyboard,
    item_key,
    results_keyboard,
)
from telegram_bot.services import training as workout
from telegram_bot.services.api import NosiFitAPIError
from telegram_bot.states.training import TrainingStates

router = Router()

RECENT_LIMIT = 6
SEARCH_LIMIT = 8
MAX_QUERY_LENGTH = 64
MENU_TEXTS = {NUTRITION, TRAINING, WATER, WEIGHT, LOGIN, LOGOUT}
GENERIC_ERROR = "Щось пішло не так. Спробуйте ще раз."

_locks: dict[int, asyncio.Lock] = {}


def _lock(user_id: int) -> asyncio.Lock:
    lock = _locks.get(user_id)
    if lock is None:
        lock = _locks[user_id] = asyncio.Lock()
    return lock


def _api(user_id: int):
    from telegram_bot.runtime import get_api

    return get_api(user_id)


def _human(exc: NosiFitAPIError, fallback: str) -> str:
    """The API client's text when it says something specific, else ``fallback``."""
    text = str(exc)
    return fallback if not text or text == GENERIC_ERROR else text


async def _safe_edit(message: Message, text: str, reply_markup=None) -> None:
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc).lower():
            raise


# --- State ------------------------------------------------------------------------


async def _load(user_id: int, state: FSMContext) -> dict:
    """Today's workout and recent exercises from the server into the state."""
    api = _api(user_id)
    session = await asyncio.to_thread(api.get_today_session)
    recent = await asyncio.to_thread(api.get_recent_exercises, "uk", RECENT_LIMIT)
    items = [workout.item_from_session(row) for row in (session or {}).get("exercises", [])]
    data = await state.get_data()
    await state.set_state(TrainingStates.active)
    await state.update_data(
        tr_sid=(session or {}).get("id"),
        tr_items=items,
        tr_saved=workout.signature(items),
        tr_rev=int(data.get("tr_rev") or 0) + 1,
        tr_recent=recent,
        tr_results=[],
        tr_query="",
        tr_more=False,
        tr_open=None,
    )
    return await state.get_data()


async def _data(user_id: int, state: FSMContext) -> dict:
    """The workout in the state; reloaded after /cancel, a restart or a
    finished workout."""
    data = await state.get_data()
    if "tr_items" not in data or await state.get_state() != TrainingStates.active.state:
        data = await _load(user_id, state)
    return data


async def _save(user_id: int, state: FSMContext, data: dict, items: list[dict]) -> str | None:
    """Store ``items`` as today's workout. Error text, or None when saved."""
    signature = workout.signature(items)
    session_id = data.get("tr_sid")
    if signature != data.get("tr_saved"):
        try:
            result = await asyncio.to_thread(
                _api(user_id).save_session, workout.payload(items), session_id
            )
        except NosiFitAPIError as exc:
            if exc.code == "session_not_found":
                await _load(user_id, state)
                return (
                    "Тренування за цей день уже закрите — показую сьогоднішнє. "
                    "Повторіть останню дію."
                )
            return _human(exc, "Не вдалося зберегти. Спробуйте ще раз.")
        session_id = result.get("id")
    await state.update_data(
        tr_items=items,
        tr_sid=session_id,
        tr_saved=signature,
        tr_rev=int(data.get("tr_rev") or 0) + 1,
    )
    return None


# --- Screens -------------------------------------------------------------------


def _home_view(data: dict) -> tuple[str, object]:
    items = data.get("tr_items") or []
    done = workout.logged(items)
    in_workout = {item["id"] for item in done}
    recent = [ex for ex in data.get("tr_recent") or [] if str(ex["id"]) not in in_workout]

    lines = ["🏋️ <b>Тренування</b>", ""]
    if done:
        lines.append("Сьогодні:")
        for n, item in enumerate(done, start=1):
            lines.append(f"{n}. {workout.escape(item['name'])} — {workout.format_logged(item)}")
        exercises, sets = workout.totals(items)
        lines += ["", f"Всього: {workout.count_exercises(exercises)} · {workout.count_sets(sets)}", ""]
        lines.append("Наступна вправа — напишіть її назву.")
    else:
        lines += ["Сьогодні ще немає вправ.", ""]
        lines.append("Напишіть назву вправи, наприклад «жим»" + (", або оберіть нещодавню:" if recent else "."))
    return "\n".join(lines), home_keyboard(items, recent)


def _card_view(data: dict, index: int) -> tuple[str, object]:
    item = data["tr_items"][index]
    lines = [f"🏋️ <b>{workout.escape(item['name'])}</b>"]
    last = workout.format_last(item.get("last"), item)
    if last:
        lines.append(f"Минулого разу: {last}")
    lines.append("")
    if item["sets"]:
        lines.append(f"Сьогодні: {workout.format_logged(item)}")
    else:
        lines.append("Сьогодні: ще немає підходів")
    lines += ["", workout.quick_input_hint(item)]
    return "\n".join(lines), card_keyboard(item, index, int(data.get("tr_rev") or 0))


def _results_view(data: dict) -> tuple[str, object]:
    query = html.escape(data.get("tr_query") or "")
    results = data.get("tr_results") or []
    if not results:
        text = (
            f"🔎 <b>{query}</b>\n\n"
            "Нічого не знайдено. Спробуйте коротше, наприклад «жим» чи «тяга»."
        )
    else:
        text = f"🔎 <b>{query}</b>\n\nОберіть вправу:"
    return text, results_keyboard(results, bool(data.get("tr_more")))


async def _show(target, view: tuple[str, object]) -> None:
    """Edit the screen a button was pressed on, or answer a typed message."""
    text, markup = view
    if isinstance(target, CallbackQuery):
        await _safe_edit(target.message, text, markup)
    else:
        await target.answer(text, reply_markup=markup)


async def _redraw_if_reloaded(target, state: FSMContext, before: dict) -> None:
    """After a failed save that reloaded today's workout (a new day), show it
    right away instead of the screen that no longer matches."""
    data = await state.get_data()
    if data.get("tr_sid") != before.get("tr_sid") or data.get("tr_open") != before.get("tr_open"):
        await _show(target, _home_view(data))


def _drop_drafts(items: list[dict]) -> list[dict]:
    return [item for item in items if item["sets"] > 0]


async def _go_home(user_id: int, state: FSMContext, data: dict) -> dict:
    """Leave the open exercise; drafts without sets disappear from the list."""
    items = data.get("tr_items") or []
    kept = _drop_drafts(items)
    update = {"tr_open": None}
    if len(kept) != len(items):
        update.update(tr_items=kept, tr_rev=int(data.get("tr_rev") or 0) + 1)
    await state.update_data(**update)
    return await state.get_data()


async def _open_exercise(user_id: int, state: FSMContext, data: dict, exercise: dict) -> dict:
    """Card of ``exercise``: the one already in the workout, or a new draft."""
    items = _drop_drafts(copy.deepcopy(data.get("tr_items") or []))
    index = next((i for i, item in enumerate(items) if item["id"] == str(exercise["id"])), None)
    if index is None:
        items.append(workout.item_from_exercise(exercise))
        index = len(items) - 1
    elif exercise.get("last") and not items[index].get("last"):
        items[index]["last"] = exercise["last"]
    await state.update_data(tr_items=items, tr_open=index, tr_rev=int(data.get("tr_rev") or 0) + 1)
    return await state.get_data()


async def _load_failed(target, exc: NosiFitAPIError) -> None:
    text = _human(exc, "Не вдалося завантажити тренування. Спробуйте ще раз.")
    if isinstance(target, CallbackQuery):
        await target.answer(text, show_alert=True)
    else:
        from telegram_bot.runtime import is_authenticated

        await target.answer(
            text, reply_markup=main_menu(authenticated=is_authenticated(target.from_user.id))
        )


# --- Entry, search, cancel -------------------------------------------------------


@router.message(F.text == TRAINING)
async def training(message: Message, state: FSMContext) -> None:
    async with _lock(message.from_user.id):
        await state.clear()
        try:
            data = await _load(message.from_user.id, state)
        except NosiFitAPIError as exc:
            await _load_failed(message, exc)
            return
    await _show(message, _home_view(data))


@router.message(TrainingStates.active, Command("cancel"))
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Скасовано. Усе, що ви вже записали, збережено.",
        reply_markup=main_menu(authenticated=True),
    )


def _workout_text(message: Message) -> bool:
    text = message.text or ""
    return bool(text.strip()) and not text.startswith("/") and text not in MENU_TEXTS


@router.message(TrainingStates.active, F.text, _workout_text)
async def typed(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    async with _lock(user_id):
        try:
            data = await _data(user_id, state)
        except NosiFitAPIError as exc:
            await _load_failed(message, exc)
            return

        index = data.get("tr_open")
        items = data.get("tr_items") or []
        if index is not None and index < len(items):
            parsed = workout.parse_quick_input(message.text, items[index])
            if parsed is not None:
                await _log_typed_set(message, state, data, index, *parsed)
                return
        await _search(message, state, message.text.strip()[:MAX_QUERY_LENGTH], offset=0)


async def _log_typed_set(message, state, data, index, changes, error) -> None:
    items = copy.deepcopy(data["tr_items"])
    item = items[index]
    error = error or workout.apply(item, changes) or workout.add_set(item)
    if error:
        await message.answer(error)
        return
    error = await _save(message.from_user.id, state, data, items)
    if error:
        await message.answer(error)
        await _redraw_if_reloaded(message, state, data)
        return
    data = await state.get_data()
    await _show(message, _card_view(data, index))


async def _search(target, state: FSMContext, query: str, offset: int) -> None:
    user_id = target.from_user.id
    try:
        found = await asyncio.to_thread(
            _api(user_id).search_exercises, query, "uk", SEARCH_LIMIT, offset
        )
    except NosiFitAPIError as exc:
        text = _human(exc, "Не вдалося виконати пошук. Спробуйте ще раз.")
        if isinstance(target, CallbackQuery):
            await target.answer(text, show_alert=True)
        else:
            await target.answer(text)
        return
    data = await state.get_data()
    results = (data.get("tr_results") or []) + found.get("items", []) if offset else found.get("items", [])
    # Typed numbers go to a set only while an exercise card is on screen.
    await state.update_data(
        tr_results=results, tr_query=query, tr_more=bool(found.get("has_more")), tr_open=None
    )
    await _show(target, _results_view(await state.get_data()))


# --- Callbacks ---------------------------------------------------------------------


def _parts(callback: CallbackQuery) -> list[str]:
    return (callback.data or "").split(":")


def _int(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


async def _stale(callback: CallbackQuery, state: FSMContext, data: dict) -> None:
    """A button of an older screen: redraw the current one instead."""
    await callback.answer("Екран оновлено.")
    index = data.get("tr_open")
    if index is not None and index < len(data.get("tr_items") or []):
        await _show(callback, _card_view(data, index))
    else:
        await _show(callback, _home_view(data))


@router.callback_query(F.data.startswith("tr:"))
async def on_button(callback: CallbackQuery, state: FSMContext) -> None:
    user_id = callback.from_user.id
    parts = _parts(callback)
    action = parts[1] if len(parts) > 1 else ""
    async with _lock(user_id):
        if action == "close":
            await state.clear()
            await callback.answer()
            await _safe_edit(callback.message, "🏋️ Тренування закрито. Записане збережено.")
            return
        if action == "finyes":
            await _finish(callback, state)
            return
        try:
            data = await _data(user_id, state)
        except NosiFitAPIError as exc:
            await _load_failed(callback, exc)
            return
        handler = _ACTIONS.get(action)
        if handler is None:
            await callback.answer()
            await _show(callback, _home_view(data))
            return
        await handler(callback, state, data, parts[2:])


async def _home(callback, state, data, args) -> None:
    data = await _go_home(callback.from_user.id, state, data)
    await callback.answer()
    await _show(callback, _home_view(data))


async def _pick_from(source: str, callback, state, data, args) -> None:
    index = _int(args[0]) if args else None
    options = data.get(source) or []
    if index is None or not 0 <= index < len(options):
        await _stale(callback, state, data)
        return
    data = await _open_exercise(callback.from_user.id, state, data, options[index])
    await callback.answer()
    await _show(callback, _card_view(data, data["tr_open"]))


async def _recent(callback, state, data, args) -> None:
    await _pick_from("tr_recent", callback, state, data, args)


async def _pick(callback, state, data, args) -> None:
    await _pick_from("tr_results", callback, state, data, args)


async def _more(callback, state, data, args) -> None:
    await callback.answer()
    if not data.get("tr_query"):
        await _show(callback, _home_view(data))
        return
    await _search(callback, state, data["tr_query"], offset=len(data.get("tr_results") or []))


async def _open(callback, state, data, args) -> None:
    index = _int(args[0]) if args else None
    items = data.get("tr_items") or []
    if index is None or not 0 <= index < len(items):
        await _stale(callback, state, data)
        return
    await state.update_data(tr_open=index)
    await callback.answer()
    await _show(callback, _card_view(await state.get_data(), index))


def _checked_index(data: dict, args: list[str]) -> int | None:
    """Index of a revision-checked button, None when the screen is stale."""
    if len(args) < 2:
        return None
    index, rev = _int(args[0]), _int(args[1])
    items = data.get("tr_items") or []
    if index is None or rev != int(data.get("tr_rev") or 0) or not 0 <= index < len(items):
        return None
    return index


def _keyed_index(data: dict, args: list[str]) -> int | None:
    """Index of a +/- button, None when it points at another exercise now."""
    index = _int(args[0]) if args else None
    items = data.get("tr_items") or []
    if index is None or not 0 <= index < len(items) or len(args) < 2:
        return None
    return index if item_key(items[index]) == args[1] else None


async def _change(callback, state, data, index, change, toast=None) -> None:
    """Apply ``change(item)`` to exercise ``index``, save, redraw its card."""
    items = copy.deepcopy(data["tr_items"])
    error = change(items[index])
    if error:
        await callback.answer(error, show_alert=True)
        return
    error = await _save(callback.from_user.id, state, data, items)
    if error:
        await callback.answer(error, show_alert=True)
        await _redraw_if_reloaded(callback, state, data)
        return
    await state.update_data(tr_open=index)
    await callback.answer(toast)
    await _show(callback, _card_view(await state.get_data(), index))


async def _add(callback, state, data, args) -> None:
    index = _checked_index(data, args)
    if index is None:
        await _stale(callback, state, data)
        return
    await _change(callback, state, data, index, workout.add_set, "Підхід записано")


async def _sub(callback, state, data, args) -> None:
    index = _checked_index(data, args)
    if index is None:
        await _stale(callback, state, data)
        return
    await _change(callback, state, data, index, workout.remove_set, "Підхід видалено")


async def _adjust(callback, state, data, args) -> None:
    index = _keyed_index(data, args)
    if index is None or len(args) < 4:
        await _stale(callback, state, data)
        return
    field = args[2]
    try:
        delta = float(args[3])
    except ValueError:
        await _stale(callback, state, data)
        return
    await _change(callback, state, data, index, lambda item: workout.adjust(item, field, delta))


async def _rir(callback, state, data, args) -> None:
    index = _keyed_index(data, args)
    if index is None or len(args) < 3:
        await _stale(callback, state, data)
        return
    value = None if args[2] == "x" else _int(args[2])
    if value is None and args[2] != "x":
        await _stale(callback, state, data)
        return
    await _change(callback, state, data, index, lambda item: workout.set_rir(item, value))


async def _ask_delete(callback, state, data, args) -> None:
    index = _checked_index(data, args)
    if index is None:
        await _stale(callback, state, data)
        return
    item = data["tr_items"][index]
    await callback.answer()
    await _safe_edit(
        callback.message,
        f"Видалити «{workout.escape(item['name'])}» "
        f"({workout.count_sets(item['sets'])}) з тренування?",
        delete_keyboard(index, int(data.get("tr_rev") or 0)),
    )


async def _delete(callback, state, data, args) -> None:
    index = _checked_index(data, args)
    if index is None:
        await _stale(callback, state, data)
        return
    items = copy.deepcopy(data["tr_items"])
    removed = items.pop(index)
    error = await _save(callback.from_user.id, state, data, items)
    if error:
        await callback.answer(error, show_alert=True)
        await _redraw_if_reloaded(callback, state, data)
        return
    await state.update_data(tr_open=None)
    await callback.answer(f"«{workout.short_name(removed['name'])}» видалено")
    await _show(callback, _home_view(await state.get_data()))


async def _ask_finish(callback, state, data, args) -> None:
    exercises, sets = workout.totals(data.get("tr_items") or [])
    if not sets:
        await callback.answer("Ще немає жодного підходу.", show_alert=True)
        return
    await callback.answer()
    await _safe_edit(
        callback.message,
        "Завершити тренування?\n\n"
        f"{workout.count_sets(sets)} · {workout.count_exercises(exercises)}",
        finish_keyboard(),
    )


async def _finish(callback: CallbackQuery, state: FSMContext) -> None:
    """Everything is saved already; confirm what the server has and leave.
    Pressing it again (or after a restart) shows the same summary."""
    try:
        session = await asyncio.to_thread(_api(callback.from_user.id).get_today_session)
    except NosiFitAPIError as exc:
        await callback.answer(
            _human(exc, "Не вдалося перевірити тренування. Спробуйте ще раз."), show_alert=True
        )
        return
    await state.clear()
    await callback.answer()
    totals = (session or {}).get("totals") or {}
    if not totals.get("sets"):
        await _safe_edit(callback.message, "🏋️ Сьогодні немає записаних вправ.")
        return
    await _safe_edit(
        callback.message,
        "✅ <b>Тренування збережено</b>\n\n"
        f"{workout.count_exercises(totals['exercises'])} · {workout.count_sets(totals['sets'])}",
    )


_ACTIONS = {
    "home": _home,
    "rc": _recent,
    "pick": _pick,
    "more": _more,
    "open": _open,
    "add": _add,
    "sub": _sub,
    "adj": _adjust,
    "rir": _rir,
    "del": _ask_delete,
    "delyes": _delete,
    "finish": _ask_finish,
}
