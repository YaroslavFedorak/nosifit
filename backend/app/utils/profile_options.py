"""The goal and activity choices offered on every form and shown on every page.

One list for the whole site: registration, profile completion and the profile
editor render these options, and the profile page shows their labels
(common.json, ``profileOptions``). Older accounts hold other spellings; they
are folded into these values when shown and when saved.
"""

# Stored value -> label key under ``profileOptions.goals`` (likewise
# ``genders`` and ``experience``). Gender has two values because the calorie
# formula has two.
GENDERS = ("male", "female")

EXPERIENCES = ("beginner", "intermediate", "advanced")


GOALS = (
    "fat_loss",
    "muscle_gain",
    "recomposition",
    "strength",
    "maintenance",
)

# Stored value (the activity factor, which also fits the 10-character column)
# -> label key under ``profileOptions.activity``.
ACTIVITIES = (
    ("1.2", "minimum"),
    ("1.375", "light"),
    ("1.55", "moderate"),
    ("1.725", "high"),
    ("1.9", "veryHigh"),
)

# Spellings written by earlier forms. "performance" is fed at maintenance by
# the nutrition model, so it is shown as that.
_GOAL_ALIASES = {
    "lose": "fat_loss",
    "weight_loss": "fat_loss",
    "gain": "muscle_gain",
    "maintain": "maintenance",
    "performance": "maintenance",
}

_EXPERIENCE_ALIASES = {
    "experienced": "advanced",
    "novice": "beginner",
    "elite": "advanced",
}

_ACTIVITY_LABELS = {
    "sedentary": "1.2",
    "light": "1.375",
    "moderate": "1.55",
    "active": "1.725",
    "very_active": "1.9",
}

WORKOUTS_PER_WEEK = tuple(range(0, 8))


def normalize_goal(value):
    """The canonical goal for a stored one; unknown values come back as they are."""
    goal = (value or "").strip().lower() if isinstance(value, str) else value
    return _GOAL_ALIASES.get(goal, goal) or None


def normalize_experience(value):
    """The canonical experience level for a stored one; unknown values stay as they are."""
    level = (value or "").strip().lower() if isinstance(value, str) else value
    return _EXPERIENCE_ALIASES.get(level, level) or None


def normalize_activity(value):
    """The canonical activity value (a factor as text) for a label or a factor."""
    if value is None or isinstance(value, bool):
        return None

    text = str(value).strip().lower()
    if text in _ACTIVITY_LABELS:
        return _ACTIVITY_LABELS[text]

    try:
        factor = float(text)
    except ValueError:
        return text or None

    if not 1.2 <= factor <= 1.9:
        return text

    return min((v for v, _ in ACTIVITIES), key=lambda v: abs(float(v) - factor))
