from typing import List

from backend.app.training.models.exercise import Exercise

# Catalog movement patterns grouped into the families used for balance
# analysis. Keeping the families coarse stops related patterns (e.g. squat
# and lunge, or the anti-movement core patterns) from being judged "weak"
# just because the training volume is split between them.
PATTERN_FAMILIES = {
    "squat": "squat",
    "lunge": "squat",
    "hinge": "hinge",
    "push": "push",
    "pull": "pull",
    "carry": "carry",
    "core": "core",
    "rotation": "core",
    "anti-rotation": "core",
    "anti-extension": "core",
    "anti-lateral-flexion": "core",
    "jump": "conditioning",
    "locomotion": "conditioning",
    "full-body": "conditioning",
}

MOVEMENT_PATTERNS = tuple(dict.fromkeys(PATTERN_FAMILIES.values()))


def pattern_key(pattern: str) -> str:
    value = (pattern or "").strip().lower().replace("_", "-")

    return PATTERN_FAMILIES.get(value, "other")


def primary_muscles(exercise: Exercise) -> List[str]:
    return [str(muscle).lower() for muscle in (exercise.muscles_primary or [])]


def secondary_muscles(exercise: Exercise) -> List[str]:
    return [str(muscle).lower() for muscle in (exercise.muscles_secondary or [])]


def movement_pattern(exercise: Exercise) -> str:
    return pattern_key(exercise.movement_pattern)

