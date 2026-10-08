"""Inline buttons of the workout steps.

Callback data (64 bytes at most); <key> is the start of the exercise id:
    tr:rc:<i> / tr:pick:<i>     exercise i of recent / search results
    tr:more                     more search results
    tr:w:<kg> / tr:c:<n>        answer the weight / reps (seconds) question
    tr:again:<key>:<sets>       one more set with the same values
    tr:other:<key>              one more set with other values
    tr:done                     back to today's workout
    tr:ex:<key>                 one exercise of today's workout
    tr:dec:<key>:<sets>         one set less
    tr:edit:<key>               change kg / reps of the exercise
    tr:del:<key> / tr:delok:<key>   delete the exercise (ask / confirm)
    tr:finish / tr:finok        finish the workout (ask / confirm)

<sets> is how many sets the screen showed: a second tap on the same
button finds more sets on the server and is ignored.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from telegram_bot.services.training import format_number, format_set, key_of, short_name


def _b(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def _markup(rows) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[row for row in rows if row])


def exercise_choice(exercises: list[dict], prefix: str, has_more: bool = False) -> InlineKeyboardMarkup:
    rows = [[_b(short_name(ex["name"], 40), f"tr:{prefix}:{i}")] for i, ex in enumerate(exercises)]
    if has_more:
        rows.append([_b("Ще результати", "tr:more")])
    return _markup(rows)


def suggestion(text: str, data: str) -> InlineKeyboardMarkup:
    """The value from last time as a one-tap answer."""
    return _markup([[_b(text, data)]])


def weight_suggestion(load: float) -> InlineKeyboardMarkup | None:
    return suggestion(f"{format_number(load)} кг", f"tr:w:{format_number(load).replace(',', '.')}") if load else None


def count_suggestion(count: int | None, duration: bool) -> InlineKeyboardMarkup | None:
    if not count:
        return None
    return suggestion(f"{count} с" if duration else f"{count} повт.", f"tr:c:{count}")


def after_set(item: dict) -> InlineKeyboardMarkup:
    key = key_of(item["id"])
    return _markup([
        [_b(f"➕ Ще підхід · {format_set(item)}", f"tr:again:{key}:{item['sets']}")],
        [_b("✏️ Інші значення", f"tr:other:{key}"), _b("✅ Готово", "tr:done")],
    ])


def workout_list(items: list[dict]) -> InlineKeyboardMarkup:
    rows = [
        [_b(f"{n}. {short_name(item['name'])}", f"tr:ex:{key_of(item['id'])}")]
        for n, item in enumerate(items, start=1)
    ]
    if items:
        rows.append([_b("✅ Завершити тренування", "tr:finish")])
    return _markup(rows)


def exercise_actions(item: dict) -> InlineKeyboardMarkup:
    key = key_of(item["id"])
    return _markup([
        [_b("➕ Ще підхід", f"tr:again:{key}:{item['sets']}"), _b("➖ Прибрати підхід", f"tr:dec:{key}:{item['sets']}")],
        [_b("✏️ Змінити", f"tr:edit:{key}"), _b("🗑 Видалити", f"tr:del:{key}")],
        [_b("← До тренування", "tr:done")],
    ])


def confirm(yes_text: str, yes_data: str, back_data: str = "tr:done") -> InlineKeyboardMarkup:
    return _markup([[_b(yes_text, yes_data), _b("← Назад", back_data)]])
