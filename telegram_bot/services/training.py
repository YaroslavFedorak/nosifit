"""Today's workout as the bot sends it to the NosiFit API.

The server keeps one row per exercise (sets x reps or seconds, kg, RPE).
Every change in the bot starts from the server's current workout, changes
one exercise and sends the whole list to /api/training/sessions/complete,
which replaces the session's exercises. The bot keeps no copy of its own,
so changes made on the website are never overwritten.
"""

import html
import re

DEFAULT_REPS = 10
DEFAULT_SECONDS = 30

# Same limits as the API.
MAX_SETS = 100
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


def item_from_session(row: dict) -> dict:
    """A logged exercise. ``reps_text`` and ``rpe`` keep what is stored
    ("8-12", 7.5) so re-sending the list changes nothing by accident."""
    duration = is_duration(row)
    item = {
        "id": str(row["id"]),
        "name": row.get("name") or "Вправа",
        "measurement_type": row.get("measurement_type"),
        "load_type": row.get("load_type"),
        "accepts_load": bool(row.get("accepts_load")),
        "sets": int(row.get("sets") or 0),
        "reps": None if duration else int(row.get("reps_count") or DEFAULT_REPS),
        "seconds": int(row.get("duration_sec") or DEFAULT_SECONDS) if duration else None,
        "load": _load_of(row.get("load")),
        "rpe": row.get("rpe"),
    }
    if not duration and row.get("reps") not in (None, ""):
        item["reps_text"] = str(row["reps"])
    return item


def new_item(exercise: dict) -> dict:
    return item_from_session({**exercise, "sets": 0, "reps": None, "reps_count": None, "rpe": None, "load": 0})


def find(items: list[dict], key: str) -> int | None:
    return next((i for i, item in enumerate(items) if key_of(item["id"]) == key), None)


def set_values(item: dict, *, count: int | None, load: float | None) -> None:
    """Reps (or seconds) and kg of the exercise, as entered."""
    if count is not None:
        if item["reps"] is None:
            item["seconds"] = count
        else:
            item["reps"] = count
            item.pop("reps_text", None)
    if load is not None:
        item["load"] = round(load, 2)


def payload(items: list[dict]) -> list[dict]:
    """The exercises list of /sessions/complete (exercises with sets only)."""
    result = []
    for item in items:
        if item["sets"] <= 0:
            continue
        entry = {"exercise": {"id": item["id"]}, "sets": item["sets"], "load": item["load"] or 0}
        if item["reps"] is None:
            entry["duration_sec"] = item["seconds"]
        else:
            entry["reps"] = item.get("reps_text") or item["reps"]
        if item.get("rpe") is not None:
            entry["rpe"] = item["rpe"]
        result.append(entry)
    return result


def totals(items: list[dict]) -> tuple[int, int]:
    done = [item for item in items if item["sets"] > 0]
    return len(done), sum(item["sets"] for item in done)


# --- Input ------------------------------------------------------------------------


def parse_number(text: str) -> float | None:
    match = _NUMBER_RE.search(text or "")
    return float(match.group().replace(",", ".")) if match else None


def check_load(value: float | None) -> str | None:
    if value is None or not 0 <= value <= MAX_LOAD:
        return f"Напишіть вагу числом від 0 до {format_number(MAX_LOAD)}, наприклад 60 або 62,5."
    return None


def check_count(value: float | None, duration: bool) -> str | None:
    limit, what = (MAX_SECONDS, "секунд") if duration else (MAX_REPS, "повторів")
    if value is None or value != int(value) or not 1 <= value <= limit:
        return f"Напишіть ціле число {what} від 1 до {limit}."
    return None


# --- Text -----------------------------------------------------------------------------


def format_number(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".").replace(".", ",")


def _plural(count: int, one: str, few: str, many: str) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return one
    if 2 <= count % 10 <= 4 and not 12 <= count % 100 <= 14:
        return few
    return many


def count_sets(count: int) -> str:
    return f"{count} {_plural(count, 'підхід', 'підходи', 'підходів')}"


def count_exercises(count: int) -> str:
    return f"{count} {_plural(count, 'вправа', 'вправи', 'вправ')}"


def format_set(item: dict) -> str:
    """One set: "60 кг × 10", "× 12", "45 с"."""
    if item["reps"] is None:
        effort = f"{item['seconds']} с"
    else:
        effort = f"× {item.get('reps_text') or item['reps']}"
    if item["load"] and item["accepts_load"]:
        prefix = "+" if item.get("load_type") == "bodyweight" else ""
        return f"{prefix}{format_number(item['load'])} кг {effort}"
    return effort


def format_logged(item: dict) -> str:
    """"3 підходи · 60 кг × 10"."""
    return f"{count_sets(item['sets'])} · {format_set(item)}"


def format_last(last: dict | None, exercise: dict) -> str | None:
    if not last or not last.get("sets"):
        return None
    return format_logged(item_from_session({**exercise, **last}))


def short_name(name: str, limit: int = 32) -> str:
    return name if len(name) <= limit else name[: limit - 1].rstrip() + "…"


def escape(text: str) -> str:
    return html.escape(text or "")
