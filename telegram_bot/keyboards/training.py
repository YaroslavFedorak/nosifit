"""Inline keyboards of the workout flow.

Callback data (all under 64 bytes):
    tr:home                      today's workout
    tr:open:<i>                  card of exercise i of the workout
    tr:rc:<i> / tr:pick:<i>      exercise i of recent / search results
    tr:more                      more search results
    tr:add:<i>:<rev>             one more set          (revision-checked)
    tr:sub:<i>:<rev>             one set less          (revision-checked)
    tr:del:<i>:<rev>             ask to delete         (revision-checked)
    tr:delyes:<i>:<rev>          delete the exercise   (revision-checked)
    tr:adj:<i>:<key>:<f>:<d>     reps / seconds / kg by d (f = r / s / l)
    tr:rir:<i>:<key>:<v>         RIR v, "x" clears it
    tr:finish / tr:finyes        finish the workout (ask / confirm)
    tr:close                     leave the flow

<rev> is the workout revision the screen was drawn from: a second tap on
"one more set" after the first one was saved is recognised and ignored.
<key> identifies the exercise (start of its id), so +/- buttons of an older
screen never change a different exercise after the list shifted.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from telegram_bot.services.training import (
    LOAD_STEP,
    SECONDS_STEP,
    format_effort,
    format_number,
    short_name,
)

RIR_CHOICES = (0, 1, 2, 3, 4)


def item_key(item: dict) -> str:
    return str(item["id"])[:12]


def _button(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def _pairs(buttons: list[InlineKeyboardButton]) -> list[list[InlineKeyboardButton]]:
    return [buttons[i: i + 2] for i in range(0, len(buttons), 2)]


def home_keyboard(items: list[dict], recent: list[dict]) -> InlineKeyboardMarkup:
    rows = _pairs(
        [_button(f"⭐ {short_name(ex['name'], 22)}", f"tr:rc:{i}") for i, ex in enumerate(recent)]
    )
    rows += [
        [_button(f"✏️ {n}. {short_name(item['name'])}", f"tr:open:{i}")]
        for n, (i, item) in enumerate(
            ((i, item) for i, item in enumerate(items) if item["sets"] > 0), start=1
        )
    ]
    if any(item["sets"] > 0 for item in items):
        rows.append([_button("✅ Завершити", "tr:finish"), _button("✖️ Закрити", "tr:close")])
    else:
        rows.append([_button("❌ Скасувати", "tr:close")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def results_keyboard(results: list[dict], has_more: bool) -> InlineKeyboardMarkup:
    rows = [[_button(short_name(ex["name"], 40), f"tr:pick:{i}")] for i, ex in enumerate(results)]
    if has_more:
        rows.append([_button("Ще результати", "tr:more")])
    rows.append([_button("← Тренування", "tr:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def card_keyboard(item: dict, index: int, rev: int) -> InlineKeyboardMarkup:
    key = item_key(item)
    rows = [[_button(f"➕ Підхід · {format_effort(item)}", f"tr:add:{index}:{rev}")]]

    if item["duration"]:
        rows.append([
            _button(f"−{SECONDS_STEP} с", f"tr:adj:{index}:{key}:s:-{SECONDS_STEP}"),
            _button(f"+{SECONDS_STEP} с", f"tr:adj:{index}:{key}:s:{SECONDS_STEP}"),
        ])
    else:
        rows.append([
            _button("−1 повт", f"tr:adj:{index}:{key}:r:-1"),
            _button("+1 повт", f"tr:adj:{index}:{key}:r:1"),
        ])
    if item["accepts_load"]:
        step = format_number(LOAD_STEP)
        rows.append([
            _button(f"−{step} кг", f"tr:adj:{index}:{key}:l:-{LOAD_STEP}"),
            _button(f"+{step} кг", f"tr:adj:{index}:{key}:l:{LOAD_STEP}"),
        ])

    current = item.get("rir")
    rir_row = []
    for value in RIR_CHOICES:
        label = f"{value}+" if value == RIR_CHOICES[-1] else str(value)
        if value == RIR_CHOICES[0]:
            label = f"RIR {label}"
        selected = current is not None and (
            current == value or (value == RIR_CHOICES[-1] and current > value)
        )
        # Tapping the selected value clears the rating.
        rir_row.append(
            _button(f"• {label}", f"tr:rir:{index}:{key}:x")
            if selected
            else _button(label, f"tr:rir:{index}:{key}:{value}")
        )
    rows.append(rir_row)

    if item["sets"] > 0:
        rows.append([
            _button("➖ Підхід", f"tr:sub:{index}:{rev}"),
            _button("🗑 Вправу", f"tr:del:{index}:{rev}"),
        ])
    rows.append([_button("← Тренування", "tr:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def delete_keyboard(index: int, rev: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            _button("🗑 Так, видалити", f"tr:delyes:{index}:{rev}"),
            _button("← Ні", f"tr:open:{index}"),
        ]]
    )


def finish_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[_button("✅ Завершити", "tr:finyes"), _button("← Назад", "tr:home")]]
    )
