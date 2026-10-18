"""🏋️ Training: log today's workout set by set.

    ➕ Add exercise → name → how many sets → for each set: reps (or
    seconds), then kg (if the exercise has a weight) → saved

Every set keeps its own reps and kg (12 × 60, 11 × 55, 8 × 50). "↻" fills a
set like the previous one (or like last time) with one tap.

📋 My workout lists today's exercises; each one can get one more set,
lose its last set, be entered again or deleted, and the workout can be
finished.

Every change reads the workout from the server first and sends it back with
one exercise changed (see telegram_bot.services.training), so the bot never
overwrites what was logged on the website. Changes of one user run one at a
time; "remove the last set" carries the number of sets its screen showed,
so a repeated tap is recognised and ignored.
"""

import asyncio

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from telegram_bot import i18n
from telegram_bot.i18n import t
from telegram_bot.keyboards import training as kb
from telegram_bot.keyboards.main import (
    ADD_EXERCISE,
    MENU_TEXTS,
    MY_WORKOUT,
    TRAINING,
    button,
    training_menu,
)
from telegram_bot.services import training as workout
from telegram_bot.services.api import NosiFitAPIError
from telegram_bot.states.training import TrainingStates

router = Router()

RECENT_LIMIT = 6
SEARCH_LIMIT = 8
MAX_QUERY_LENGTH = 64
ALREADY_DONE = "already"

_locks: dict[int, asyncio.Lock] = {}


def _lock(user_id: int) -> asyncio.Lock:
    return _locks.setdefault(user_id, asyncio.Lock())


def _api(user_id: int):
    from telegram_bot.runtime import get_api

    return get_api(user_id)


def _human(exc: NosiFitAPIError, fallback: str) -> str:
    text = str(exc)
    return fallback if not text or text == t("err.generic") else text


async def _edit(message: Message, text: str, markup=None) -> None:
    try:
        await message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc).lower():
            raise


async def _reply(target, text: str, markup=None) -> None:
    """Edit the screen of a pressed button, or answer a typed message."""
    if isinstance(target, CallbackQuery):
        await _edit(target.message, text, markup)
    else:
        await target.answer(text, reply_markup=markup)


async def _fail(target, text: str) -> None:
    if isinstance(target, CallbackQuery):
        await target.answer(text, show_alert=True)
    else:
        await target.answer(text)


# --- Server -------------------------------------------------------------------------


async def _today(user_id: int) -> tuple[int | None, list[dict]]:
    session = await asyncio.to_thread(_api(user_id).get_today_session)
    if not session:
        return None, []
    return session["id"], [workout.item_from_session(row) for row in session["exercises"]]


async def _change(user_id: int, key: str, change, exercise: dict | None = None):
    """Apply ``change(item)`` to one exercise of the server's current workout
    and save. ``exercise`` adds it when it is not logged yet.
    Returns (error text or None, changed item, whole list)."""
    session_id, items = await _today(user_id)
    index = workout.find(items, key)
    if index is None:
        if exercise is None:
            return t("tr.not_in_workout"), None, items
        items.append(workout.new_item(exercise))
        index = len(items) - 1
    item = items[index]
    error = change(item)
    if error:
        return error, item, items
    if not item["entries"]:
        items.pop(index)
    await asyncio.to_thread(_api(user_id).save_session, workout.payload(items), session_id)
    return None, item, items


# --- Screens -----------------------------------------------------------------------


def _summary(items: list[dict]) -> str:
    lines = [t("tr.today"), ""]
    if not items:
        lines.append(t("tr.empty"))
        return "\n".join(lines)
    for n, item in enumerate(items, start=1):
        lines.append(f"{n}. <b>{workout.escape(item['name'])}</b> — {workout.format_sets_inline(item)}")
    exercises, sets = workout.totals(items)
    lines += [
        "",
        t("tr.total", exercises=workout.count_exercises(exercises), sets=workout.count_sets(sets)),
    ]
    return "\n".join(lines)


def _exercise_text(item: dict, title: str = "") -> str:
    head = f"{title}\n\n" if title else ""
    return f"{head}🏋️ <b>{workout.escape(item['name'])}</b>\n{workout.format_sets_block(item)}"


async def _show_workout(target, user_id: int) -> None:
    _, items = await _today(user_id)
    await _reply(target, _summary(items), kb.workout_list(items))


# --- Mode, add exercise, search ----------------------------------------------------


@router.message(button(TRAINING))
async def training(message: Message, state: FSMContext) -> None:
    await state.clear()
    try:
        _, items = await _today(message.from_user.id)
    except NosiFitAPIError as exc:
        await message.answer(_human(exc, t("tr.load_failed")))
        return
    await message.answer(_summary(items), reply_markup=training_menu())


@router.message(button(MY_WORKOUT))
async def my_workout(message: Message, state: FSMContext) -> None:
    await state.clear()
    try:
        await _show_workout(message, message.from_user.id)
    except NosiFitAPIError as exc:
        await message.answer(_human(exc, t("tr.load_failed")))


@router.message(button(ADD_EXERCISE))
async def add_exercise(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(TrainingStates.searching)
    try:
        recent = await asyncio.to_thread(
            _api(message.from_user.id).get_recent_exercises, i18n.current_language(), RECENT_LIMIT
        )
    except NosiFitAPIError:
        recent = []
    await state.update_data(tr_recent=recent)
    text = t("tr.search_prompt")
    if recent:
        text += "\n\n" + t("tr.recent_hint")
    await message.answer(text, reply_markup=kb.exercise_choice(recent, "rc"))


@router.message(TrainingStates.searching, Command("cancel"))
@router.message(TrainingStates.sets, Command("cancel"))
@router.message(TrainingStates.weight, Command("cancel"))
@router.message(TrainingStates.count, Command("cancel"))
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(t("tr.cancelled"), reply_markup=training_menu())


def _typed(message: Message) -> bool:
    text = message.text or ""
    return bool(text.strip()) and not text.startswith("/") and text not in MENU_TEXTS


@router.message(TrainingStates.searching, F.text, _typed)
async def search(message: Message, state: FSMContext) -> None:
    await _search(message, state, message.text.strip()[:MAX_QUERY_LENGTH], offset=0)


async def _search(target, state: FSMContext, query: str, offset: int) -> None:
    try:
        found = await asyncio.to_thread(
            _api(target.from_user.id).search_exercises,
            query,
            i18n.current_language(),
            SEARCH_LIMIT,
            offset,
        )
    except NosiFitAPIError as exc:
        await _fail(target, _human(exc, t("tr.search_failed")))
        return
    data = await state.get_data()
    results = (data.get("tr_results") or []) + found["items"] if offset else found["items"]
    await state.update_data(tr_results=results, tr_query=query)
    if not results:
        await _reply(
            target,
            t("tr.nothing_found", query=workout.escape(query)),
        )
        return
    await _reply(
        target,
        t("tr.choose_exercise", query=workout.escape(query)),
        kb.exercise_choice(results, "pick", bool(found.get("has_more"))),
    )


# --- Sets, reps, weight ---------------------------------------------------------------
#
# State data while entering: tr_ex (the exercise), tr_mode ("add" appends
# the sets, "replace" enters the exercise again), tr_total (sets to enter),
# tr_entries (sets entered so far), tr_count (reps of the current set),
# tr_ref (sets to suggest: last time's, or the logged ones).


async def _begin(target, state: FSMContext, exercise: dict, mode: str, total: int | None, note: str = "") -> None:
    logged = exercise.get("entries") or []
    if mode == "replace":
        ref, ref_label, prev = logged, "tr.as_before", None
    elif logged:  # one more set of a logged exercise
        ref, ref_label, prev = [], "", logged[-1]
    else:
        ref, ref_label, prev = (exercise.get("last") or {}).get("set_entries") or [], "tr.as_last_time", None
    await state.update_data(
        tr_ex=exercise, tr_mode=mode, tr_total=total, tr_entries=[],
        tr_ref=ref, tr_ref_label=ref_label, tr_prev=prev, tr_note=note,
    )
    if total is None:
        await state.set_state(TrainingStates.sets)
        head = _head(exercise, note)
        await _reply(target, head + t("tr.how_many_sets"), kb.sets_choice(len(ref) or None))
    else:
        await _ask_count(target, state)


def _head(exercise: dict, note: str = "", step: str = "") -> str:
    title = f"🏋️ <b>{workout.escape(exercise['name'])}</b>" + (f" · {step}" if step else "")
    return title + (f"\n{note}" if note else "") + "\n\n"


async def _ask_count(target, state: FSMContext) -> None:
    data = await state.get_data()
    exercise, entries, total = data["tr_ex"], data["tr_entries"], data["tr_total"]
    number = len(entries) + 1
    step = t("tr.set_of", number=number, total=total) if total > 1 else t("tr.set_single")
    await state.set_state(TrainingStates.count)
    question = t("tr.how_many_seconds") if workout.is_duration(exercise) else t("tr.how_many_reps")
    await _reply(
        target,
        _head(exercise, data.get("tr_note", ""), step) + question,
        kb.count_choice(exercise, _suggestions(data)),
    )


def _suggestions(data: dict) -> list[tuple[str, dict, str]]:
    """Sets the current one can copy: the previous set, and the set with
    the same number last time (or before re-entering)."""
    entries, ref = data.get("tr_entries") or [], data.get("tr_ref") or []
    options = []
    previous = entries[-1] if entries else data.get("tr_prev")
    if previous:
        options.append((t("tr.as_previous"), previous, "p"))
    if len(entries) < len(ref) and ref[len(entries)] != previous:
        options.append((t(data.get("tr_ref_label") or "tr.as_before"), ref[len(entries)], "r"))
    return options


def _suggested_load(data: dict) -> float | None:
    options = _suggestions(data)
    return options[0][1].get("load") if options else None


async def _take_sets(target, state: FSMContext, value: float | None) -> None:
    error = workout.check_sets(value)
    if error:
        await _fail(target, error)
        return
    await state.update_data(tr_total=int(value))
    await _ask_count(target, state)


async def _take_count(target, state: FSMContext, value: float | None) -> None:
    data = await state.get_data()
    exercise = data.get("tr_ex")
    if exercise is None:
        await _fail(target, t("tr.pick_again"))
        return
    error = workout.check_count(value, workout.is_duration(exercise))
    if error:
        await _fail(target, error)
        return
    if not workout.asks_weight(exercise):
        await _add_entry(target, state, {workout.count_key(exercise): int(value), "load": 0.0})
        return
    await state.update_data(tr_count=int(value))
    await state.set_state(TrainingStates.weight)
    unit = t("unit.sec") if workout.is_duration(exercise) else t("unit.reps")
    await _reply(
        target,
        _head(exercise, data.get("tr_note", ""), f"{int(value)} {unit}") + t("tr.how_much_weight"),
        kb.weight_choice(_suggested_load(data)),
    )


async def _take_weight(target, state: FSMContext, value: float | None) -> None:
    error = workout.check_load(value)
    if error:
        await _fail(target, error)
        return
    data = await state.get_data()
    exercise = data["tr_ex"]
    await _add_entry(target, state, {workout.count_key(exercise): data["tr_count"], "load": round(value, 2)})


async def _add_entry(target, state: FSMContext, entry: dict) -> None:
    data = await state.get_data()
    entries = data["tr_entries"] + [entry]
    await state.update_data(tr_entries=entries)
    if len(entries) < data["tr_total"]:
        await _ask_count(target, state)
        return
    await _commit(target, state)


async def _commit(target, state: FSMContext) -> None:
    data = await state.get_data()
    exercise, mode, entries = data["tr_ex"], data["tr_mode"], data["tr_entries"]

    def change(item):
        new = (item["entries"] + entries) if mode == "add" else entries
        if len(new) > workout.MAX_SETS:
            return t("tr.max_sets", max=workout.MAX_SETS)
        item["entries"] = new
        return None

    user_id = target.from_user.id
    async with _lock(user_id):
        try:
            error, item, _ = await _change(
                user_id, workout.key_of(exercise["id"]), change, exercise
            )
        except NosiFitAPIError as exc:
            await _fail(target, _human(exc, t("tr.save_failed")))
            return
    if error:
        await _fail(target, error)
        return
    await state.clear()
    await _reply(target, _exercise_text(item, t("tr.logged")), kb.after_sets(item))


@router.message(TrainingStates.sets, F.text, _typed)
async def typed_sets(message: Message, state: FSMContext) -> None:
    await _take_sets(message, state, workout.parse_number(message.text))


@router.message(TrainingStates.count, F.text, _typed)
async def typed_count(message: Message, state: FSMContext) -> None:
    await _take_count(message, state, workout.parse_number(message.text))


@router.message(TrainingStates.weight, F.text, _typed)
async def typed_weight(message: Message, state: FSMContext) -> None:
    await _take_weight(message, state, workout.parse_number(message.text))


# --- Buttons --------------------------------------------------------------------------


@router.callback_query(F.data.startswith("tr:"))
async def on_button(callback: CallbackQuery, state: FSMContext) -> None:
    parts = (callback.data or "").split(":")
    handler = _ACTIONS.get(parts[1] if len(parts) > 1 else "")
    try:
        if handler is not None:
            await handler(callback, state, parts[2:])
    except NosiFitAPIError as exc:
        await callback.answer(_human(exc, t("tr.save_failed_short")), show_alert=True)
        return
    try:
        await callback.answer()
    except TelegramBadRequest:
        pass  # a handler already answered it


async def _pick_from(source: str, callback, state, args) -> None:
    options = (await state.get_data()).get(source) or []
    index = int(args[0]) if args and args[0].isdigit() else -1
    if not 0 <= index < len(options):
        await callback.answer(t("tr.list_stale"), show_alert=True)
        return
    exercise = options[index]
    last = workout.format_last(exercise.get("last"), exercise)
    await _begin(callback, state, exercise, "add", None, t("tr.last_time", sets=last) if last else "")


async def _recent(callback, state, args) -> None:
    await _pick_from("tr_recent", callback, state, args)


async def _pick(callback, state, args) -> None:
    await _pick_from("tr_results", callback, state, args)


async def _more(callback, state, args) -> None:
    data = await state.get_data()
    if data.get("tr_query"):
        await _search(callback, state, data["tr_query"], offset=len(data.get("tr_results") or []))


def _in_state(expected):
    async def check(state: FSMContext) -> bool:
        return await state.get_state() == expected.state

    return check


async def _sets_button(callback, state, args) -> None:
    if await _in_state(TrainingStates.sets)(state):
        await _take_sets(callback, state, workout.parse_number(args[0] if args else ""))


async def _count_button(callback, state, args) -> None:
    if await _in_state(TrainingStates.count)(state):
        await _take_count(callback, state, workout.parse_number(args[0] if args else ""))


async def _weight_button(callback, state, args) -> None:
    if await _in_state(TrainingStates.weight)(state):
        await _take_weight(callback, state, workout.parse_number(args[0] if args else ""))


async def _same(callback, state, args) -> None:
    """Fill the current set like the suggested one."""
    if not await _in_state(TrainingStates.count)(state):
        return
    code = args[0] if args else "p"
    chosen = next((entry for _, entry, c in _suggestions(await state.get_data()) if c == code), None)
    if chosen:
        await _add_entry(callback, state, dict(chosen))


async def _less(callback, state, args) -> None:
    key = args[0] if args else ""
    expected = int(args[1]) if len(args) > 1 and args[1].isdigit() else None

    def change(item):
        if expected is not None and len(item["entries"]) != expected:
            return ALREADY_DONE
        item["entries"] = item["entries"][:-1]
        return None

    async with _lock(callback.from_user.id):
        error, item, items = await _change(callback.from_user.id, key, change)
    if error == ALREADY_DONE:
        await callback.answer(t("tr.set_removed"))
    elif error:
        await callback.answer(error, show_alert=True)
        return
    if item["entries"]:
        await _edit(callback.message, _exercise_text(item), kb.exercise_actions(item))
    else:
        await _edit(callback.message, _summary(items), kb.workout_list(items))


async def _logged_item(callback, key: str) -> dict | None:
    _, items = await _today(callback.from_user.id)
    index = workout.find(items, key)
    if index is None:
        await callback.answer(t("tr.not_in_workout"), show_alert=True)
        await _edit(callback.message, _summary(items), kb.workout_list(items))
        return None
    return items[index]


async def _one_more(callback, state, args) -> None:
    item = await _logged_item(callback, args[0] if args else "")
    if item:
        await _begin(callback, state, item, "add", 1)


async def _redo(callback, state, args) -> None:
    item = await _logged_item(callback, args[0] if args else "")
    if item:
        await _begin(callback, state, item, "replace", None, t("tr.now", sets=workout.format_sets_inline(item)))


async def _exercise(callback, state, args) -> None:
    await state.clear()
    item = await _logged_item(callback, args[0] if args else "")
    if item:
        await _edit(callback.message, _exercise_text(item), kb.exercise_actions(item))


async def _done(callback, state, args) -> None:
    await state.clear()
    await _show_workout(callback, callback.from_user.id)


async def _ask_delete(callback, state, args) -> None:
    item = await _logged_item(callback, args[0] if args else "")
    if item:
        await _edit(
            callback.message,
            t(
                "tr.delete_ask",
                name=workout.escape(item["name"]),
                sets=workout.count_sets(len(item["entries"])),
            ),
            kb.confirm(t("tr.btn.delete"), f"tr:delok:{args[0]}", f"tr:ex:{args[0]}"),
        )


async def _delete(callback, state, args) -> None:
    def change(item):
        item["entries"] = []
        return None

    async with _lock(callback.from_user.id):
        error, _, items = await _change(callback.from_user.id, args[0] if args else "", change)
    if error:
        await callback.answer(error, show_alert=True)
    await _edit(callback.message, _summary(items), kb.workout_list(items))


async def _ask_finish(callback, state, args) -> None:
    _, items = await _today(callback.from_user.id)
    exercises, sets = workout.totals(items)
    if not sets:
        await callback.answer(t("tr.no_sets_yet"), show_alert=True)
        return
    await _edit(
        callback.message,
        t("tr.finish_ask", exercises=workout.count_exercises(exercises), sets=workout.count_sets(sets)),
        kb.confirm(t("tr.btn.finish_ok"), "tr:finok"),
    )


async def _finish(callback, state, args) -> None:
    """Everything is saved after each set; this confirms what the server has."""
    await state.clear()
    _, items = await _today(callback.from_user.id)
    exercises, sets = workout.totals(items)
    if not sets:
        await _edit(callback.message, t("tr.no_logged"))
        return
    await _edit(
        callback.message,
        t("tr.saved", exercises=workout.count_exercises(exercises), sets=workout.count_sets(sets)),
    )


_ACTIONS = {
    "rc": _recent,
    "pick": _pick,
    "more": _more,
    "n": _sets_button,
    "c": _count_button,
    "w": _weight_button,
    "same": _same,
    "one": _one_more,
    "redo": _redo,
    "dec": _less,
    "ex": _exercise,
    "done": _done,
    "del": _ask_delete,
    "delok": _delete,
    "finish": _ask_finish,
    "finok": _finish,
}
