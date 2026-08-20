from typing import List

from myapp.app.training_engine.models.exercise import Exercise

MOVEMENT_PATTERNS = (
    "push",
    "pull",
    "hinge",
    "squat",
    "core",
    "carry",
    "rotation",
)


def pattern_key(pattern: str) -> str:
    value = (pattern or "").lower()

    for pattern_name in MOVEMENT_PATTERNS:
        if pattern_name in value:
            return pattern_name

    return "other"


def primary_muscles(exercise: Exercise) -> List[str]:
    return [str(muscle).lower() for muscle in (exercise.muscles_primary or [])]


def secondary_muscles(exercise: Exercise) -> List[str]:
    return [str(muscle).lower() for muscle in (exercise.muscles_secondary or [])]


def movement_pattern(exercise: Exercise) -> str:
    return pattern_key(exercise.movement_pattern)
