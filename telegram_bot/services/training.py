"""The workout being logged from Telegram.

The bot holds today's list of exercises the way the server stores it (sets x
reps or seconds, kg and RIR per exercise) and sends the whole list to
/api/training/sessions/complete after every change; the server replaces the
session's exercises. No training maths happens here: this module only builds
that list, formats it and reads the quick "60 10 2" input.

An item with 0 sets is a draft: the exercise is open on screen but nothing
is logged yet, so it is not sent.
"""

import html
import json
import re

DEFAULT_REPS = 10
DEFAULT_SECONDS = 30
LOAD_STEP = 2.5
SECONDS_STEP = 5

# Same limits as the API.
MAX_SETS = 100
MAX_REPS = 100
MAX_SECONDS = 3600
MAX_LOAD = 2000.0
MAX_RIR = 9

NAME_IN_BUTTON = 28

_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")
# Unit words and "x" separators that may surround the numbers of one set.
_UNITS_RE = re.compile(r"кг|kg|повт\w*|сек\w*|rir|\bс\b|[x×х*/]", re.I)
_ONLY_NUMBERS_RE = re.compile(r"[\d\s.,]+")
_TIMES_RE = re.compile(r"\d\s*[x×х*]\s*\d", re.I)


def _load_of(value) -> float:
    try:
        return max(float(value or 0), 0.0)
    except (TypeError, ValueError):
        return 0.0


def item_from_exercise(exercise: dict) -> dict:
    """A draft for an exercise from search or recent, prefilled from last time."""
    last = exercise.get("last") or {}
    duration = exercise.get("measurement_type") == "duration"
    accepts_load = bool(exercise.get("accepts_load"))
    return {
        "id": str(exercise["id"]),
        "name": exercise.get("name") or "Вправа",
        "duration": duration,
        "accepts_load": accepts_load,
        "bodyweight": exercise.get("load_type") == "bodyweight",
        "sets": 0,
        "reps": None if duration else int(last.get("reps_count") or DEFAULT_REPS),
        "seconds": int(last.get("duration_sec") or DEFAULT_SECONDS) if duration else None,
        "load": _load_of(last.get("load")) if accepts_load else 0.0,
        "rir": last.get("rir"),
        "last": last or None,
    }


def item_from_session(row: dict) -> dict:
    """An exercise already logged today. ``reps_text`` / ``rpe`` keep what
    is stored ("8-12", 7.5) until the user changes that value here."""
    item = item_from_exercise({**row, "last": None})
    item.update(
        sets=int(row.get("sets") or 0),
        load=_load_of(row.get("load")),
        rir=row.get("rir"),
    )
    if item["duration"]:
        item["seconds"] = int(row.get("duration_sec") or DEFAULT_SECONDS)
    else:
        item["reps"] = int(row.get("reps_count") or DEFAULT_REPS)
        if row.get("reps") not in (None, ""):
            item["reps_text"] = str(row["reps"])
    if row.get("rpe") is not None:
        item["rpe"] = row["rpe"]
    return item


def logged(items: list[dict]) -> list[dict]:
    return [item for item in items if item.get("sets", 0) > 0]


def payload(items: list[dict]) -> list[dict]:
    """The exercises list of /sessions/complete."""
    result = []
    for item in logged(items):
        entry = {"exercise": {"id": item["id"]}, "sets": item["sets"], "load": item["load"] or 0}
        if item["duration"]:
            entry["duration_sec"] = item["seconds"]
        else:
            entry["reps"] = item.get("reps_text") or item["reps"]
        if "rpe" in item:
            entry["rpe"] = item["rpe"]
        else:
            entry["rir"] = item.get("rir")
        result.append(entry)
    return result


def signature(items: list[dict]) -> str:
    return json.dumps(payload(items), sort_keys=True, ensure_ascii=False)


def totals(items: list[dict]) -> tuple[int, int]:
    done = logged(items)
    return len(done), sum(item["sets"] for item in done)


# --- Changes (each returns an error text or None) ---------------------------


def set_reps(item: dict, reps: int) -> str | None:
    if not 1 <= reps <= MAX_REPS:
        return f"Повтори: від 1 до {MAX_REPS}."
    item["reps"] = reps
    item.pop("reps_text", None)
    return None


def set_seconds(item: dict, seconds: int) -> str | None:
    if not 1 <= seconds <= MAX_SECONDS:
        return f"Час: від 1 до {MAX_SECONDS} секунд."
    item["seconds"] = seconds
    return None


def set_load(item: dict, load: float) -> str | None:
    if not 0 <= load <= MAX_LOAD:
        return f"Вага: від 0 до {format_number(MAX_LOAD)} кг."
    item["load"] = round(load, 2)
    return None


def set_rir(item: dict, rir: int | None) -> str | None:
    if rir is not None and not 0 <= rir <= MAX_RIR:
        return f"RIR: від 0 до {MAX_RIR}."
    item["rir"] = rir
    item.pop("rpe", None)
    return None


def adjust(item: dict, field: str, delta: float) -> str | None:
    if field == "r" and not item["duration"]:
        return set_reps(item, max(1, item["reps"] + int(delta)))
    if field == "s" and item["duration"]:
        return set_seconds(item, max(SECONDS_STEP, item["seconds"] + int(delta)))
    if field == "l" and item["accepts_load"]:
        return set_load(item, max(0.0, item["load"] + delta))
    return "Цю величину тут не змінити."


def add_set(item: dict) -> str | None:
    if item["sets"] >= MAX_SETS:
        return f"Не більше {MAX_SETS} підходів."
    item["sets"] += 1
    return None


def remove_set(item: dict) -> str | None:
    if item["sets"] <= 0:
        return "Підходів уже немає."
    item["sets"] -= 1
    return None


def _number(text: str) -> float:
    return float(text.replace(",", "."))


def parse_quick_input(text: str, item: dict):
    """One set typed as numbers. None: the text is not numbers (a search).
    Otherwise (changes, error); changes are applied with ``apply``."""
    value = (text or "").strip().lower()
    if not value or not _ONLY_NUMBERS_RE.fullmatch(_UNITS_RE.sub(" ", value)):
        return None
    numbers = [_number(n) for n in _NUMBER_RE.findall(value)]
    if not numbers or len(numbers) > 3:
        return None

    primary = "seconds" if item["duration"] else "reps"
    explicit_load = bool(_TIMES_RE.search(value))
    weighted = item["accepts_load"] and (not item["bodyweight"] or explicit_load)

    changes = {}
    if weighted and len(numbers) >= 2:
        changes["load"] = numbers[0]
        changes[primary] = numbers[1]
        if len(numbers) == 3:
            changes["rir"] = numbers[2]
    else:
        if len(numbers) == 3:
            return {}, "Забагато чисел. " + quick_input_hint(item)
        changes[primary] = numbers[0]
        if len(numbers) == 2:
            changes["rir"] = numbers[1]

    for key in ("reps", "seconds", "rir"):
        if key in changes:
            if changes[key] != int(changes[key]):
                return {}, "Повтори, секунди й RIR — цілі числа."
            changes[key] = int(changes[key])
    return changes, None


def apply(item: dict, changes: dict) -> str | None:
    setters = {"load": set_load, "reps": set_reps, "seconds": set_seconds, "rir": set_rir}
    for key, value in changes.items():
        error = setters[key](item, value)
        if error:
            return error
    return None


def quick_input_hint(item: dict) -> str:
    if item["duration"]:
        return "Напишіть секунди, наприклад «45» або «45 2» (секунди, RIR)."
    if item["accepts_load"] and not item["bodyweight"]:
        return "Напишіть вагу й повтори: «60 10» або «60 10 2» (кг, повтори, RIR)."
    if item["accepts_load"]:
        return "Напишіть повтори: «12» або «12 2» (повтори, RIR). З обтяженням: «10x12»."
    return "Напишіть повтори: «12» або «12 2» (повтори, RIR)."


# --- Formatting ---------------------------------------------------------------


def format_number(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".").replace(".", ",")


def _plural_sets(count: int) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return "підхід"
    if 2 <= count % 10 <= 4 and not 12 <= count % 100 <= 14:
        return "підходи"
    return "підходів"


def _plural_exercises(count: int) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return "вправа"
    if 2 <= count % 10 <= 4 and not 12 <= count % 100 <= 14:
        return "вправи"
    return "вправ"


def count_sets(count: int) -> str:
    return f"{count} {_plural_sets(count)}"


def count_exercises(count: int) -> str:
    return f"{count} {_plural_exercises(count)}"


def format_load(item: dict) -> str:
    if not item["accepts_load"] or not item["load"]:
        return ""
    sign = "+" if item["bodyweight"] else ""
    return f"{sign}{format_number(item['load'])} кг"


def format_effort(item: dict) -> str:
    """"10 · 60 кг · RIR 2" (one set's values)."""
    parts = [f"{item['seconds']} с" if item["duration"] else str(item.get("reps_text") or item["reps"])]
    load = format_load(item)
    if load:
        parts.append(load)
    if item.get("rir") is not None:
        parts.append(f"RIR {item['rir']}")
    return " · ".join(parts)


def format_logged(item: dict) -> str:
    """"3 × 10 · 60 кг · RIR 2"."""
    return f"{item['sets']} × {format_effort(item)}"


def format_last(last: dict | None, item: dict) -> str | None:
    if not last or not last.get("sets"):
        return None
    previous = {
        **item,
        "sets": last["sets"],
        "reps": last.get("reps_count") or item.get("reps"),
        "reps_text": last.get("reps"),
        "seconds": last.get("duration_sec") or item.get("seconds"),
        "load": _load_of(last.get("load")),
        "rir": last.get("rir"),
    }
    return format_logged(previous)


def short_name(name: str, limit: int = NAME_IN_BUTTON) -> str:
    return name if len(name) <= limit else name[: limit - 1].rstrip() + "…"


def escape(text: str) -> str:
    return html.escape(text or "")
