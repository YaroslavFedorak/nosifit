"""Validation of workout data sent by clients."""

import re

from backend.app.training.models.exercise import Exercise
from backend.app.utils.validation import ValidationError, bounded_number

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
    """Validated sets/reps/load/rpe of one exercise in a session."""
    if not isinstance(data, dict):
        raise ValidationError("exercise data must be an object")
    cleaned = {}
    if "sets_done" in data:
        cleaned["sets_done"] = bounded_number(data["sets_done"], 0, 100, integer=True)
    if "reps_done" in data:
        cleaned["reps_done"] = clean_reps(data["reps_done"])
    if "load_done" in data:
        cleaned["load_done"] = bounded_number(data["load_done"], 0, 2000)
    if "rpe" in data:
        cleaned["rpe"] = bounded_number(data["rpe"], 0, 10)
    return cleaned


def clean_fatigue(value):
    return bounded_number(value, 0, 10, integer=True)


def clean_exercise_id(value):
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValidationError("exercise id is invalid")
    exercise_id = str(value).strip()
    if not exercise_id or len(exercise_id) > 64 or not Exercise.query.get(exercise_id):
        raise ValidationError("exercise not found")
    return exercise_id


