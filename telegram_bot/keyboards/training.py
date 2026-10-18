"""Inline buttons of the workout steps.

Callback data (64 bytes at most); <key> is the start of the exercise id:
    tr:rc:<i> / tr:pick:<i>     exercise i of recent / search results
    tr:more                     more search results
    tr:n:<sets>                 answer "how many sets"
    tr:c:<n> / tr:w:<kg>        answer reps (seconds) / kg of the current set
    tr:same:<p|r>               the current set like the previous one (p)
                                or like the same set last time (r)
    tr:one:<key>                log one more set
    tr:redo:<key>               enter all sets of the exercise again
    tr:done                     back to today's workout
    tr:ex:<key>                 one exercise of today's workout
    tr:dec:<key>:<sets>         remove the last set (sets = count on screen)
    tr:del:<key> / tr:delok:<key>   delete the exercise (ask / confirm)
    tr:finish / tr:finok        finish the workout (ask / confirm)
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from telegram_bot.i18n import t
from telegram_bot.services.training import format_entry, format_number, key_of, short_name

SET_CHOICES = (1, 2, 3, 4, 5)


def _b(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def _markup(rows) -> InlineKeyboardMarkup | None:
    rows = [row for row in rows if row]
    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None


def exercise_choice(exercises: list[dict], prefix: str, has_more: bool = False):
    rows = [[_b(short_name(ex["name"], 40), f"tr:{prefix}:{i}")] for i, ex in enumerate(exercises)]
    if has_more:
        rows.append([_b(t("tr.btn.more_results"), "tr:more")])
    return _markup(rows)


def sets_choice(last_count: int | None):
    return _markup([[
        _b(f"• {n}" if n == last_count else str(n), f"tr:n:{n}") for n in SET_CHOICES
    ]])


def count_choice(item: dict, options: list[tuple[str, dict, str]]):
    """Whole sets to repeat with one tap: (label, set, "p" or "r")."""
    return _markup([[_b(f"↻ {label}: {format_entry(item, entry)}", f"tr:same:{code}")] for label, entry, code in options])


def weight_choice(load: float | None):
    if not load:
        return None
    return _markup([[_b(f"{format_number(load)} {t('unit.kg')}", f"tr:w:{format_number(load).replace(',', '.')}")]])


def after_sets(item: dict):
    key = key_of(item["id"])
    return _markup([
        [_b(t("tr.btn.another_set"), f"tr:one:{key}"), _b(t("tr.btn.redo"), f"tr:redo:{key}")],
        [_b(t("tr.btn.done"), "tr:done")],
    ])


def workout_list(items: list[dict]):
    rows = [
        [_b(f"{n}. {short_name(item['name'])}", f"tr:ex:{key_of(item['id'])}")]
        for n, item in enumerate(items, start=1)
    ]
    if items:
        rows.append([_b(t("tr.btn.finish"), "tr:finish")])
    return _markup(rows)


def exercise_actions(item: dict):
    key = key_of(item["id"])
    return _markup([
        [_b(t("tr.btn.add_set"), f"tr:one:{key}"), _b(t("tr.btn.last_set"), f"tr:dec:{key}:{len(item['entries'])}")],
        [_b(t("tr.btn.redo"), f"tr:redo:{key}"), _b(t("tr.btn.delete"), f"tr:del:{key}")],
        [_b(t("tr.btn.to_workout"), "tr:done")],
    ])


def confirm(yes_text: str, yes_data: str, back_data: str = "tr:done"):
    return _markup([[_b(yes_text, yes_data), _b(t("tr.btn.back"), back_data)]])
