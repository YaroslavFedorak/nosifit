"""Today's workout as the bot sends it to the NosiFit API.

Each exercise is a list of sets, every set with its own reps (or seconds)
and kg. Every change in the bot starts from the server's current workout,
changes one exercise and sends the whole list to
/api/training/sessions/complete, which replaces the session's exercises.
The bot keeps no copy of its own, so changes made on the website are never
overwritten.
"""

import html
import re

from telegram_bot.i18n import current_language, plural, t

MAX_SETS = 30
MAX_REPS = 100
MAX_SECONDS = 3600
MAX_LOAD = 2000.0

KEY_LENGTH = 12

_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")


def _load_of(value) -> float:
    try:
        return max(float(value or 0), 0.0)
    except (TypeError, ValueError):
        return 0.0


def key_of(exercise_id) -> str:
    """Short exercise id for callback data (64 bytes at most)."""
    return str(exercise_id)[:KEY_LENGTH]


def asks_weight(exercise: dict) -> bool:
    """Weight is asked for barbell, dumbbell, machine and cable exercises."""
    return bool(exercise.get("accepts_load")) and exercise.get("load_type") != "bodyweight"


def is_duration(exercise: dict) -> bool:
    return exercise.get("measurement_type") == "duration"


def count_key(exercise: dict) -> str:
    return "duration_sec" if is_duration(exercise) else "reps"


def item_from_session(row: dict) -> dict:
    """A logged exercise with its sets. ``rpe`` is kept as stored."""
    return {
        "id": str(row["id"]),
        "name": row.get("name") or t("tr.exercise_default"),
        "measurement_type": row.get("measurement_type"),
        "load_type": row.get("load_type"),
        "accepts_load": bool(row.get("accepts_load")),
        "entries": [dict(entry) for entry in row.get("set_entries") or []],
        "rpe": row.get("rpe"),
    }


def new_item(exercise: dict) -> dict:
    return item_from_session({**exercise, "set_entries": [], "rpe": None})


def find(items: list[dict], key: str) -> int | None:
    return next((i for i, item in enumerate(items) if key_of(item["id"]) == key), None)


def payload(items: list[dict]) -> list[dict]:
    """The exercises list of /sessions/complete (exercises with sets only)."""
    result = []
    for item in items:
        if not item["entries"]:
            continue
        entry = {"exercise": {"id": item["id"]}, "set_entries": item["entries"]}
        if item.get("rpe") is not None:
            entry["rpe"] = item["rpe"]
        result.append(entry)
    return result


def totals(items: list[dict]) -> tuple[int, int]:
    done = [item for item in items if item["entries"]]
    return len(done), sum(len(item["entries"]) for item in done)


# --- Input ------------------------------------------------------------------------


def parse_number(text: str) -> float | None:
    match = _NUMBER_RE.search(text or "")
    return float(match.group().replace(",", ".")) if match else None


def check_sets(value: float | None) -> str | None:
    if value is None or value != int(value) or not 1 <= value <= MAX_SETS:
        return t("tr.check_sets", max=MAX_SETS)
    return None


def check_load(value: float | None) -> str | None:
    if value is None or not 0 <= value <= MAX_LOAD:
        return t("tr.check_load", max=format_number(MAX_LOAD))
    return None


def check_count(value: float | None, duration: bool) -> str | None:
    limit = MAX_SECONDS if duration else MAX_REPS
    if value is None or value != int(value) or not 1 <= value <= limit:
        return t("tr.check_seconds" if duration else "tr.check_reps", limit=limit)
    return None


# --- Text -----------------------------------------------------------------------------


def format_number(value: float) -> str:
    # A comma for the languages that write decimals with one.
    separator = "." if current_language() == "en" else ","
    return f"{value:.2f}".rstrip("0").rstrip(".").replace(".", separator)


def count_sets(count: int) -> str:
    return f"{count} {plural(count, 'tr.plural_sets')}"


def count_exercises(count: int) -> str:
    return f"{count} {plural(count, 'tr.plural_exercises')}"


def _shows_load(item: dict) -> bool:
    return bool(item.get("accepts_load")) and any(_load_of(e.get("load")) for e in item["entries"])


def format_entry(item: dict, entry: dict) -> str:
    """One set: "12 × 60 kg", "12 reps", "45 s"."""
    if is_duration(item):
        text = f"{entry.get('duration_sec')} {t('unit.sec')}"
    else:
        text = f"{entry.get('reps')} {t('unit.reps')}"
    load = _load_of(entry.get("load"))
    if load and item.get("accepts_load"):
        sign = "+" if item.get("load_type") == "bodyweight" else ""
        unit = text.split()[0] if not is_duration(item) else text
        return f"{unit} × {sign}{format_number(load)} {t('unit.kg')}"
    return text


def format_sets_inline(item: dict) -> str:
    """"3 sets: 12×60 · 11×55 · 8×50 kg"."""
    entries = item["entries"]
    if not entries:
        return t("tr.no_sets")
    key = count_key(item)
    if _shows_load(item):
        sign = "+" if item.get("load_type") == "bodyweight" else ""
        parts = [f"{e.get(key)}×{sign}{format_number(_load_of(e.get('load')))}" for e in entries]
        unit = t("unit.sec_kg") if is_duration(item) else t("unit.kg")
    else:
        parts = [str(e.get(key)) for e in entries]
        unit = t("unit.sec") if is_duration(item) else t("unit.reps")
    return f"{count_sets(len(entries))}: {' · '.join(parts)} {unit}"


def format_sets_block(item: dict) -> str:
    """One line per set: "1. 12 × 60 kg"."""
    return "\n".join(f"{n}. {format_entry(item, e)}" for n, e in enumerate(item["entries"], start=1))


def format_last(last: dict | None, exercise: dict) -> str | None:
    if not last or not last.get("set_entries"):
        return None
    return format_sets_inline(item_from_session({**exercise, **last}))


def short_name(name: str, limit: int = 32) -> str:
    return name if len(name) <= limit else name[: limit - 1].rstrip() + "…"


def escape(text: str) -> str:
    return html.escape(text or "")
