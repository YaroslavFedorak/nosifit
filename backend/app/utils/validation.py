"""Server-side validation shared by the auth and profile routes.

Frontend checks are a convenience only; everything stored comes through here.
"""

import math
import re

EMAIL_MAX_LENGTH = 120  # users.email is String(120)
USERNAME_MAX_LENGTH = 50  # users.username is String(50)
PASSWORD_MIN_LENGTH = 8
# Hashing is deliberately slow; unbounded input is a cheap CPU DoS.
PASSWORD_MAX_LENGTH = 128

_EMAIL_RE = re.compile(r"^[^@\s<>\"'(),;:\\\[\]]+@[^@\s<>\"'(),;:\\\[\]]+\.[^@\s<>\"'(),;:\\\[\]]+$")
_CHOICE_RE = re.compile(r"^[a-z0-9_.\-]+$")

# Physical profile limits (human ranges, generous on both ends).
PROFILE_RANGES = {
    "age": (10, 120, int),
    "height": (50.0, 272.0, float),
    "weight": (20.0, 400.0, float),
    "workouts_per_week": (0, 14, int),
}

# Column sizes in user_profiles.
CHOICE_MAX_LENGTH = {
    "gender": 10,
    "activity": 10,
    "goal": 20,
    "experience": 50,
    "training_location": 32,
}


class ValidationError(ValueError):
    pass


def normalize_email(value):
    email = (value or "").strip().lower()
    if not email or len(email) > EMAIL_MAX_LENGTH or not _EMAIL_RE.match(email):
        return None
    return email


def password_problem(password):
    """Return an error message, or None when the password is acceptable."""
    if not isinstance(password, str) or len(password) < PASSWORD_MIN_LENGTH:
        return f"Пароль має містити щонайменше {PASSWORD_MIN_LENGTH} символів."
    if len(password) > PASSWORD_MAX_LENGTH:
        return f"Пароль може містити не більше {PASSWORD_MAX_LENGTH} символів."
    return None


def clean_username(value):
    username = " ".join((value or "").split())
    if not username or len(username) > USERNAME_MAX_LENGTH:
        return None
    return username


def parse_profile_number(field, value, required=False):
    """Parse a profile number within PROFILE_RANGES; empty -> None."""
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            raise ValidationError(f"{field} is required")
        return None

    low, high, kind = PROFILE_RANGES[field]
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field} must be a number") from exc

    if not math.isfinite(number) or not (low <= number <= high):
        raise ValidationError(f"{field} must be between {low} and {high}")

    if kind is int:
        if number != int(number):
            raise ValidationError(f"{field} must be a whole number")
        return int(number)
    return number


def clean_choice(field, value):
    """Short machine values such as gender or goal; empty -> None."""
    choice = (value or "").strip().lower() if isinstance(value, str) else ""
    if not choice:
        return None
    if len(choice) > CHOICE_MAX_LENGTH[field] or not _CHOICE_RE.match(choice):
        raise ValidationError(f"Invalid {field}")
    return choice


def bounded_number(value, low, high, *, integer=False, allow_none=True):
    """Generic finite number in [low, high]; raises ValidationError."""
    if value is None or value == "":
        if allow_none:
            return None
        raise ValidationError("A number is required")
    if isinstance(value, bool):
        raise ValidationError("A number is required")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError("A number is required") from exc
    if not math.isfinite(number) or not (low <= number <= high):
        raise ValidationError(f"Value must be between {low} and {high}")
    if integer:
        if number != int(number):
            raise ValidationError("A whole number is required")
        return int(number)
    return number


# PostgreSQL INTEGER; larger values make the query itself fail.
DB_ID_MAX = 2**31 - 1


def as_db_id(value):
    """A positive int that fits an INTEGER id column, else None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, str) and value.strip().isdigit():
        value = int(value.strip())
    if isinstance(value, int) and 0 < value <= DB_ID_MAX:
        return value
    return None
