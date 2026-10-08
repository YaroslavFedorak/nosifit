"""Measurement-aware prescriptions shared by plans, sessions and load maths.

A repetition exercise is described by sets x reps, a duration exercise by
sets x seconds. The two never share a field and are never converted into each
other: ``reps`` is ``None`` for duration exercises and ``duration_sec`` is
``None`` for repetition ones. ``per_side`` comes from the exercise
prescription and means the reps or seconds are done on each side.
"""

import re
from typing import Any, Dict, Mapping

from .catalog import MEASUREMENT_DURATION, MEASUREMENT_REPS

DEFAULT_SETS = 3
DEFAULT_REPS = "8-12"
DEFAULT_SECONDS = 30

_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")


def _get(source: Any, key: str, default: Any = None) -> Any:
    if isinstance(source, Mapping):
        return source.get(key, default)
    return getattr(source, key, default)


def measurement_type_of(exercise: Any) -> str:
    value = _get(exercise, "measurement_type")
    return MEASUREMENT_DURATION if value == MEASUREMENT_DURATION else MEASUREMENT_REPS


def is_duration_exercise(exercise: Any) -> bool:
    return measurement_type_of(exercise) == MEASUREMENT_DURATION


def _numbers(value: Any):
    if value is None or isinstance(value, bool):
        return []
    if isinstance(value, (int, float)):
        return [float(value)]
    return [float(n.replace(",", ".")) for n in _NUMBER_RE.findall(str(value))]


def parse_count(value: Any) -> int:
    """Parse a reps or seconds value: 12, "12", "8-12" (midpoint), "45 sec"."""
    numbers = _numbers(value)
    if not numbers:
        return 0
    if len(numbers) >= 2:
        return max(int(round((numbers[0] + numbers[1]) / 2.0)), 0)
    return max(int(numbers[0]), 0)


def parse_sets(value: Any) -> int:
    numbers = _numbers(value)
    return max(int(numbers[0]), 0) if numbers else 0


def parse_load(value: Any) -> float:
    numbers = _numbers(value)
    return max(numbers[0], 0.0) if numbers else 0.0


def _prescription(exercise: Any) -> Dict[str, Any]:
    value = _get(exercise, "prescription")
    return value if isinstance(value, Mapping) else {}


def is_per_side(exercise: Any) -> bool:
    return bool(_prescription(exercise).get("per_side"))


def default_entry(exercise: Any) -> Dict[str, Any]:
    """Sets plus reps range or seconds taken from the exercise prescription."""
    prescription = _prescription(exercise)
    sets = prescription.get("sets") or DEFAULT_SETS
    per_side = is_per_side(exercise)

    if is_duration_exercise(exercise):
        low = prescription.get("seconds_min")
        high = prescription.get("seconds_max")
        if low and high:
            seconds = int(5 * round((low + high) / 2.0 / 5))
        else:
            seconds = DEFAULT_SECONDS
        return {
            "sets": sets,
            "reps": None,
            "duration_sec": seconds,
            "per_side": per_side,
        }

    low = prescription.get("reps_min")
    high = prescription.get("reps_max")
    if low and high:
        reps = str(low) if low == high else f"{low}-{high}"
    else:
        reps = DEFAULT_REPS
    return {"sets": sets, "reps": reps, "duration_sec": None, "per_side": per_side}


def build_entry(
    exercise: Any,
    sets: Any = None,
    reps: Any = None,
    duration_sec: Any = None,
    load: Any = None,
) -> Dict[str, Any]:
    """Normalise one planned or logged exercise into measurement-specific fields."""
    defaults = default_entry(exercise)
    entry = {
        "measurement_type": measurement_type_of(exercise),
        "sets": parse_sets(sets) or defaults["sets"],
        "reps": None,
        "duration_sec": None,
        "per_side": defaults["per_side"],
        "load": parse_load(load),
    }

    if entry["measurement_type"] == MEASUREMENT_DURATION:
        entry["duration_sec"] = parse_count(duration_sec) or defaults["duration_sec"]
    else:
        entry["reps"] = reps if reps not in (None, "") else defaults["reps"]

    return entry


def performed_values(session_exercise: Any, exercise: Any) -> Dict[str, Any]:
    """Sets, reps or seconds and load actually done (falling back to planned).

    Accepts ``SessionExercise`` rows (``*_done`` / ``*_planned`` columns) as
    well as plain objects or dicts with ``sets`` / ``reps`` / ``duration_sec``
    / ``load``.
    """

    def pick(done: str, planned: str, plain: str) -> Any:
        # Zero counts as "not filled in", matching how sessions are created
        # (sets_done=0) and how the API falls back to planned values.
        for key in (done, planned, plain):
            value = _get(session_exercise, key)
            if value not in (None, "") and value != 0:
                return value
        return None

    duration = is_duration_exercise(exercise)
    sets = parse_sets(pick("sets_done", "sets_planned", "sets"))
    load = parse_load(pick("load_done", "load_planned", "load"))

    if duration:
        seconds = parse_count(
            pick("duration_sec_done", "duration_sec_planned", "duration_sec")
        )
        return {
            "measurement_type": MEASUREMENT_DURATION,
            "sets": sets,
            "reps": None,
            "duration_sec": seconds,
            "load": load,
        }

    return {
        "measurement_type": MEASUREMENT_REPS,
        "sets": sets,
        "reps": parse_count(pick("reps_done", "reps_planned", "reps")),
        "duration_sec": None,
        "load": load,
    }


def session_update_fields(exercise: Any, data: Mapping[str, Any]) -> Dict[str, Any]:
    """Map a client payload onto ``SessionExercise`` columns.

    Duration exercises take ``duration_sec`` and repetition exercises take
    ``reps``; a value sent in the other field is ignored, never converted.
    """
    fields: Dict[str, Any] = {}

    for source in ("sets_done", "sets"):
        if source in data:
            fields["sets_done"] = data[source]
            break

    for source in ("load_done", "load"):
        if source in data:
            fields["load_done"] = data[source]
            break

    if "rpe" in data:
        fields["rpe"] = data["rpe"]

    if exercise is not None and is_duration_exercise(exercise):
        for source in ("duration_sec_done", "duration_sec"):
            if source in data and data[source] not in (None, ""):
                fields["duration_sec_done"] = parse_count(data[source])
                fields["reps_done"] = None
                break
    else:
        for source in ("reps_done", "reps"):
            if source in data:
                fields["reps_done"] = data[source]
                fields["duration_sec_done"] = None
                break

    if "reps_done" in fields and fields["reps_done"] is not None:
        fields["reps_done"] = str(fields["reps_done"])

    return fields


def format_entry(entry: Mapping[str, Any]) -> str:
    """Human-readable prescription: ``3 × 12``, ``3 × 45 sec``, ``3 × 10 / side``."""
    sets = entry.get("sets") or 0
    if entry.get("measurement_type") == MEASUREMENT_DURATION:
        text = f"{sets} × {entry.get('duration_sec') or 0} sec"
    else:
        text = f"{sets} × {entry.get('reps') or 0}"
    return f"{text} / side" if entry.get("per_side") else text


def serialize_entry(exercise: Any, entry: Mapping[str, Any]) -> Dict[str, Any]:
    """API representation of a planned/logged exercise."""
    return {
        "exercise": {
            "id": _get(exercise, "id"),
            "name": _get(exercise, "name"),
            "slug": _get(exercise, "slug"),
            "measurement_type": measurement_type_of(exercise),
        },
        "measurement_type": entry["measurement_type"],
        "sets": entry["sets"],
        "reps": entry["reps"],
        "duration_sec": entry["duration_sec"],
        "per_side": entry["per_side"],
        "load": entry["load"],
    }
