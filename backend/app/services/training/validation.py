"""Validation of workout data sent by clients."""

import re

from backend.app.extensions import db
from backend.app.services.training.model import parameters as P
from backend.app.training.exercises.prescription import is_duration_exercise
from backend.app.training.models.exercise import Exercise
from backend.app.utils.validation import ValidationError, bounded_number

# Clients may rate a set as reps in reserve; it is stored as RPE, the scale
# the training model reads (RIR = RPE_TO_RIR_OFFSET - RPE).
MAX_LOGGED_RIR = 9

# Repetitions are free text ("8-12", "8–12", "max"), but never markup.
REPS_RE = re.compile(r"^[\w\s\-–—/+×.,]{1,16}$")


def clean_reps(value, default=None):
    if value is None or value == "":
        return default
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValidationError("reps must be text or a number")
    text = str(value).strip()
    if not REPS_RE.match(text):
        raise ValidationError("reps has an invalid format")
    return text


def clean_set_data(data):
    """Validated sets, reps or seconds, load and rpe of one exercise in a session."""
    if not isinstance(data, dict):
        raise ValidationError("exercise data must be an object")
    cleaned = {}
    if "sets_done" in data:
        cleaned["sets_done"] = bounded_number(data["sets_done"], 0, 100, integer=True)
    if "reps_done" in data:
        cleaned["reps_done"] = clean_reps(data["reps_done"])
    if "duration_sec_done" in data:
        cleaned["duration_sec_done"] = bounded_number(
            data["duration_sec_done"], 0, 3600, integer=True
        )
    if "load_done" in data:
        cleaned["load_done"] = bounded_number(data["load_done"], 0, 2000)
    if "rpe" in data:
        cleaned["rpe"] = bounded_number(data["rpe"], 0, 10)
    if "rir" in data:
        rir = bounded_number(data["rir"], 0, MAX_LOGGED_RIR)
        # A client echoing a rated row back sends "rir": null next to its rpe.
        if rir is not None or "rpe" not in data:
            cleaned["rpe"] = rpe_from_rir(rir)
    if data.get("set_entries") is not None:
        cleaned["set_entries"] = clean_set_entries(data["set_entries"])
    return cleaned


MAX_SET_ENTRIES = 30


def clean_set_entries(value):
    """Sets as logged one by one: reps or seconds, and kg, per set."""
    if value is None:
        return None
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_SET_ENTRIES:
        raise ValidationError(f"set_entries must be a list of 1 to {MAX_SET_ENTRIES} sets")
    cleaned = []
    for entry in value:
        if not isinstance(entry, dict):
            raise ValidationError("each set must be an object")
        reps = bounded_number(entry.get("reps"), 1, 100, integer=True)
        seconds = bounded_number(entry.get("duration_sec"), 1, 3600, integer=True)
        if (reps is None) == (seconds is None):
            raise ValidationError("each set needs reps or duration_sec")
        cleaned.append(
            {
                **({"reps": reps} if reps is not None else {"duration_sec": seconds}),
                "load": bounded_number(entry.get("load"), 0, 2000) or 0.0,
            }
        )
    return cleaned


def rpe_from_rir(rir):
    return None if rir is None else float(P.RPE_TO_RIR_OFFSET) - float(rir)


def rir_from_rpe(rpe):
    """Reps in reserve of a logged RPE; None when the set was not rated."""
    if rpe is None or rpe <= 0:
        return None
    return max(int(round(float(P.RPE_TO_RIR_OFFSET) - float(rpe))), 0)


def clean_fatigue(value):
    return bounded_number(value, 0, 10, integer=True)


def clean_exercise_id(value):
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValidationError("exercise id is invalid")
    exercise_id = str(value).strip()
    if not exercise_id or len(exercise_id) > 64 or not db.session.get(Exercise, exercise_id):
        raise ValidationError("exercise not found")
    return exercise_id


def check_set_entries(exercise_id, data):
    """Logged sets must be measured the way the exercise is.

    A timed set on a repetition exercise would be stored as 0 reps.
    """
    entries = data.get("set_entries")
    if not entries:
        return data
    key = "duration_sec" if is_duration_exercise(db.session.get(Exercise, exercise_id)) else "reps"
    if any(key not in entry for entry in entries):
        raise ValidationError(f"each set of this exercise needs {key}")
    return data


def merge_repeated_exercises(items):
    """One row per exercise for ``[(exercise_id, set_data), ...]``.

    A session has one row per exercise, so an exercise listed twice in one
    save would overwrite its own earlier sets. Its sets are added up instead.
    """
    merged = {}
    for exercise_id, data in items:
        first = merged.get(exercise_id)
        if first is None:
            merged[exercise_id] = dict(data)
            continue
        if first.get("set_entries") and data.get("set_entries"):
            first["set_entries"] = first["set_entries"] + data["set_entries"]
            if len(first["set_entries"]) > MAX_SET_ENTRIES:
                raise ValidationError(f"at most {MAX_SET_ENTRIES} sets per exercise")
        else:
            first.pop("set_entries", None)
            data = {key: value for key, value in data.items() if key != "set_entries"}
            first["sets_done"] = (first.get("sets_done") or 0) + (data.get("sets_done") or 0)
        if data.get("rpe") is not None:
            first["rpe"] = data["rpe"]
    return list(merged.items())


