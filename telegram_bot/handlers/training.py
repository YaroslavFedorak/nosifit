"""🏋️ Тренування: log today's workout step by step.

    ➕ Додати вправу → name → exercise → weight (if it has one) → reps
    → "➕ Ще підхід" (same values, one tap) / "✏️ Інші значення" / "✅ Готово"

📋 Моє тренування lists today's exercises; each one can get or lose a set,
be changed or deleted, and the workout can be finished.

Every change reads the workout from the server first and sends it back with
one exercise changed (see telegram_bot.services.training), so the bot never
overwrites what was logged on the website. Changes of one user run one at a
time; buttons that add or remove a set carry the number of sets their
screen showed, so a repeated tap is recognised and ignored.
"""

import asyncio

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from telegram_bot.keyboards import training as kb
from telegram_bot.keyboards.main import ADD_EXERCISE, MENU_TEXTS, MY_WORKOUT, TRAINING, training_menu
from telegram_bot.services import training as workout
from telegram_bot.services.api import NosiFitAPIError
from telegram_bot.states.training import TrainingStates

router = Router()

RECENT_LIMIT = 6
SEARCH_LIMIT = 8
MAX_QUERY_LENGTH = 64
GENERIC_ERROR = "Щось пішло не так. Спробуйте ще раз."
ALREADY_DONE = "already"

_locks: dict[int, asyncio.Lock] = {}


def _lock(user_id: int) -> asyncio.Lock:
    return _locks.setdefault(user_id, asyncio.Lock())


def _api(user_id: int):
    from telegram_bot.runtime import get_api

    return get_api(user_id)


def _human(exc: NosiFitAPIError, fallback: str) -> str:
    text = str(exc)
    return fallback if not text or text == GENERIC_ERROR else text


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
            return "Цієї вправи вже немає в тренуванні.", None, items
        items.append(workout.new_item(exercise))
        index = len(items) - 1
    item = items[index]
    error = change(item)
    if error:
        return error, item, items
    if item["sets"] <= 0:
        items.pop(index)
    await asyncio.to_thread(_api(user_id).save_session, workout.payload(items), session_id)
    return None, item, items


# --- Screens -----------------------------------------------------------------------


def _summary(items: list[dict]) -> str:
    lines = ["🏋️ <b>Тренування сьогодні</b>", ""]
    if not items:
        lines.append("Ще немає вправ. Натисніть «➕ Додати вправу».")
        return "\n".join(lines)
    for n, item in enumerate(items, start=1):
        lines.append(f"{n}. {workout.escape(item['name'])} — {workout.format_logged(item)}")
    exercises, sets = workout.totals(items)
    lines += ["", f"Всього: {workout.count_exercises(exercises)} · {workout.count_sets(sets)}"]
    return "\n".join(lines)


def _exercise_text(item: dict) -> str:
    return f"🏋️ <b>{workout.escape(item['name'])}</b>\n\nСьогодні: {workout.format_logged(item)}"


def _set_logged_text(item: dict) -> str:
    return f"✅ Підхід записано\n\n<b>{workout.escape(item['name'])}</b>: {workout.format_logged(item)}"


async def _show_workout(target, user_id: int) -> None:
    _, items = await _today(user_id)
    await _reply(target, _summary(items), kb.workout_list(items))


# --- Mode, add exercise, search ----------------------------------------------------


@router.message(F.text == TRAINING)
async def training(message: Message, state: FSMContext) -> None:
    await state.clear()
    try:
        _, items = await _today(message.from_user.id)
    except NosiFitAPIError as exc:
        await message.answer(_human(exc, "Не вдалося завантажити тренування. Спробуйте ще раз."))
        return
    await message.answer(_summary(items), reply_markup=training_menu())


@router.message(F.text == MY_WORKOUT)
async def my_workout(message: Message, state: FSMContext) -> None:
    await state.clear()
    try:
        await _show_workout(message, message.from_user.id)
    except NosiFitAPIError as exc:
        await message.answer(_human(exc, "Не вдалося завантажити тренування. Спробуйте ще раз."))


@router.message(F.text == ADD_EXERCISE)
async def add_exercise(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(TrainingStates.searching)
    try:
        recent = await asyncio.to_thread(
            _api(message.from_user.id).get_recent_exercises, "uk", RECENT_LIMIT
        )
    except NosiFitAPIError:
        recent = []
    await state.update_data(tr_recent=recent)
    text = "🔎 Напишіть назву вправи, наприклад «жим» або «присідання»."
    if recent:
        text += "\n\nАбо оберіть одну з нещодавніх:"
    await message.answer(text, reply_markup=kb.exercise_choice(recent, "rc"))


@router.message(TrainingStates.searching, Command("cancel"))
@router.message(TrainingStates.weight, Command("cancel"))
@router.message(TrainingStates.count, Command("cancel"))
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Скасовано. Усе записане збережено.", reply_markup=training_menu())


def _typed(message: Message) -> bool:
    text = message.text or ""
    return bool(text.strip()) and not text.startswith("/") and text not in MENU_TEXTS


@router.message(TrainingStates.searching, F.text, _typed)
async def search(message: Message, state: FSMContext) -> None:
    await _search(message, state, message.text.strip()[:MAX_QUERY_LENGTH], offset=0)


async def _search(target, state: FSMContext, query: str, offset: int) -> None:
    try:
        found = await asyncio.to_thread(
            _api(target.from_user.id).search_exercises, query, "uk", SEARCH_LIMIT, offset
        )
    except NosiFitAPIError as exc:
        await _fail(target, _human(exc, "Не вдалося виконати пошук. Спробуйте ще раз."))
        return
    data = await state.get_data()
    results = (data.get("tr_results") or []) + found["items"] if offset else found["items"]
    await state.update_data(tr_results=results, tr_query=query)
    if not results:
        await _reply(
            target,
            f"🔎 «{workout.escape(query)}» — нічого не знайдено.\n\n"
            "Спробуйте коротше, наприклад «жим» чи «тяга».",
        )
        return
    await _reply(
        target,
        f"🔎 «{workout.escape(query)}»\n\nОберіть вправу:",
        kb.exercise_choice(results, "pick", bool(found.get("has_more"))),
    )


# --- Weight and reps -----------------------------------------------------------------


def _previous(exercise: dict) -> dict:
    """Values to offer: last time's for a new exercise, the current ones
    for a logged exercise."""
    duration = workout.is_duration(exercise)
    last = exercise.get("last")
    if last:
        count = last.get("duration_sec") if duration else last.get("reps_count")
        load = last.get("load")
    else:
        count = exercise.get("seconds") if duration else exercise.get("reps")
        load = exercise.get("load")
    return {"count": count, "load": float(load or 0)}


async def _ask_weight_or_count(target, state: FSMContext, exercise: dict, mode: str, note: str) -> None:
    """Start entering one set (mode "add") or new values (mode "edit")."""
    await state.update_data(tr_ex=exercise, tr_mode=mode, tr_load=None)
    header = f"🏋️ <b>{workout.escape(exercise['name'])}</b>\n" + (f"{note}\n" if note else "") + "\n"
    if workout.asks_weight(exercise):
        await state.set_state(TrainingStates.weight)
        await _reply(target, header + "Яка вага, кг?", kb.weight_suggestion(_previous(exercise)["load"]))
    else:
        await _ask_count(target, state, exercise, header)


async def _ask_count(target, state: FSMContext, exercise: dict, header: str) -> None:
    await state.set_state(TrainingStates.count)
    duration = workout.is_duration(exercise)
    question = "Скільки секунд?" if duration else "Скільки повторів?"
    await _reply(target, header + question, kb.count_suggestion(_previous(exercise)["count"], duration))


async def _start(target, state: FSMContext, exercise: dict) -> None:
    last = workout.format_last(exercise.get("last"), exercise)
    await _ask_weight_or_count(target, state, exercise, "add", f"Минулого разу: {last}" if last else "")


async def _take_weight(target, state: FSMContext, value: float | None) -> None:
    error = workout.check_load(value)
    if error:
        await _fail(target, error)
        return
    exercise = (await state.get_data())["tr_ex"]
    await state.update_data(tr_load=value)
    header = f"🏋️ <b>{workout.escape(exercise['name'])}</b> · {workout.format_number(value)} кг\n\n"
    await _ask_count(target, state, exercise, header)


async def _take_count(target, state: FSMContext, value: float | None) -> None:
    data = await state.get_data()
    exercise = data.get("tr_ex")
    if exercise is None:
        await _fail(target, "Оберіть вправу ще раз: «➕ Додати вправу».")
        return
    error = workout.check_count(value, workout.is_duration(exercise))
    if error:
        await _fail(target, error)
        return
    mode, load = data.get("tr_mode"), data.get("tr_load")

    def change(item):
        workout.set_values(item, count=int(value), load=load)
        if mode == "add":
            if item["sets"] >= workout.MAX_SETS:
                return f"Не більше {workout.MAX_SETS} підходів."
            item["sets"] += 1
        return None

    user_id = target.from_user.id
    async with _lock(user_id):
        try:
            error, item, _ = await _change(
                user_id, workout.key_of(exercise["id"]), change, exercise if mode == "add" else None
            )
        except NosiFitAPIError as exc:
            await _fail(target, _human(exc, "Не вдалося зберегти підхід. Спробуйте ще раз."))
            return
    if error:
        await _fail(target, error)
        return
    await state.clear()
    if mode == "add":
        await _reply(target, _set_logged_text(item), kb.after_set(item))
    else:
        await _reply(target, "✅ Змінено\n\n" + _exercise_text(item), kb.exercise_actions(item))


@router.message(TrainingStates.weight, F.text, _typed)
async def typed_weight(message: Message, state: FSMContext) -> None:
    await _take_weight(message, state, workout.parse_number(message.text))


@router.message(TrainingStates.count, F.text, _typed)
async def typed_count(message: Message, state: FSMContext) -> None:
    await _take_count(message, state, workout.parse_number(message.text))


# --- Buttons --------------------------------------------------------------------------


@router.callback_query(F.data.startswith("tr:"))
async def on_button(callback: CallbackQuery, state: FSMContext) -> None:
    parts = (callback.data or "").split(":")
    handler = _ACTIONS.get(parts[1] if len(parts) > 1 else "")
    try:
        if handler is not None:
            await handler(callback, state, parts[2:])
    except NosiFitAPIError as exc:
        await callback.answer(_human(exc, "Не вдалося зберегти. Спробуйте ще раз."), show_alert=True)
        return
    try:
        await callback.answer()
    except TelegramBadRequest:
        pass  # a handler already answered it


async def _pick_from(source: str, callback, state, args) -> None:
    options = (await state.get_data()).get(source) or []
    index = int(args[0]) if args and args[0].isdigit() else -1
    if not 0 <= index < len(options):
        await callback.answer("Цей список застарів. Натисніть «➕ Додати вправу».", show_alert=True)
        return
    await _start(callback, state, options[index])


async def _recent(callback, state, args) -> None:
    await _pick_from("tr_recent", callback, state, args)


async def _pick(callback, state, args) -> None:
    await _pick_from("tr_results", callback, state, args)


async def _more(callback, state, args) -> None:
    data = await state.get_data()
    if data.get("tr_query"):
        await _search(callback, state, data["tr_query"], offset=len(data.get("tr_results") or []))


async def _weight_button(callback, state, args) -> None:
    if await state.get_state() == TrainingStates.weight.state:
        await _take_weight(callback, state, workout.parse_number(args[0] if args else ""))


async def _count_button(callback, state, args) -> None:
    if await state.get_state() == TrainingStates.count.state:
        await _take_count(callback, state, workout.parse_number(args[0] if args else ""))


def _expected(args) -> tuple[str, int | None]:
    key = args[0] if args else ""
    sets = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    return key, sets


def _step(delta: int, expected: int | None):
    def change(item):
        if expected is not None and item["sets"] != expected:
            return ALREADY_DONE
        item["sets"] += delta
        return None

    return change


async def _again(callback, state, args) -> None:
    """One more set with the same values."""
    key, expected = _expected(args)
    async with _lock(callback.from_user.id):
        error, item, _ = await _change(callback.from_user.id, key, _step(1, expected))
    if error == ALREADY_DONE:
        await callback.answer("Цей підхід уже записано.")
    elif error:
        await callback.answer(error, show_alert=True)
        return
    await _edit(callback.message, _set_logged_text(item), kb.after_set(item))


async def _less(callback, state, args) -> None:
    key, expected = _expected(args)
    async with _lock(callback.from_user.id):
        error, item, items = await _change(callback.from_user.id, key, _step(-1, expected))
    if error and error != ALREADY_DONE:
        await callback.answer(error, show_alert=True)
        return
    if item["sets"] > 0:
        await _edit(callback.message, _exercise_text(item), kb.exercise_actions(item))
    else:
        await _edit(callback.message, _summary(items), kb.workout_list(items))


async def _logged_item(callback, key: str) -> dict | None:
    _, items = await _today(callback.from_user.id)
    index = workout.find(items, key)
    if index is None:
        await callback.answer("Цієї вправи вже немає в тренуванні.", show_alert=True)
        await _edit(callback.message, _summary(items), kb.workout_list(items))
        return None
    return items[index]


async def _other(callback, state, args) -> None:
    item = await _logged_item(callback, args[0] if args else "")
    if item:
        await _ask_weight_or_count(callback, state, item, "add", "Наступний підхід з іншими значеннями.")


async def _edit_values(callback, state, args) -> None:
    item = await _logged_item(callback, args[0] if args else "")
    if item:
        await _ask_weight_or_count(callback, state, item, "edit", f"Зараз: {workout.format_logged(item)}")


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
            f"Видалити «{workout.escape(item['name'])}» ({workout.count_sets(item['sets'])}) з тренування?",
            kb.confirm("🗑 Видалити", f"tr:delok:{args[0]}", f"tr:ex:{args[0]}"),
        )


async def _delete(callback, state, args) -> None:
    def change(item):
        item["sets"] = 0
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
        await callback.answer("Ще немає жодного підходу.", show_alert=True)
        return
    await _edit(
        callback.message,
        f"Завершити тренування?\n\n{workout.count_exercises(exercises)} · {workout.count_sets(sets)}",
        kb.confirm("✅ Завершити", "tr:finok"),
    )


async def _finish(callback, state, args) -> None:
    """Everything is saved after each set; this confirms what the server has."""
    await state.clear()
    _, items = await _today(callback.from_user.id)
    exercises, sets = workout.totals(items)
    if not sets:
        await _edit(callback.message, "🏋️ Сьогодні немає записаних вправ.")
        return
    await _edit(
        callback.message,
        f"✅ <b>Тренування збережено</b>\n\n{workout.count_exercises(exercises)} · {workout.count_sets(sets)}",
    )


_ACTIONS = {
    "rc": _recent,
    "pick": _pick,
    "more": _more,
    "w": _weight_button,
    "c": _count_button,
    "again": _again,
    "other": _other,
    "dec": _less,
    "edit": _edit_values,
    "ex": _exercise,
    "done": _done,
    "del": _ask_delete,
    "delok": _delete,
    "finish": _ask_finish,
    "finok": _finish,
}
