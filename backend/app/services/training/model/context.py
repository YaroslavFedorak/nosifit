"""User context of the training model and the domain-level normalisers.

Only parameters with a defensible effect on training decisions are read:
goal, experience, training frequency, weak points / onboarding focus,
available equipment / location and body weight (tonnage only). Age, sex,
BMI and activity level deliberately do not enter the model.
"""

from dataclasses import dataclass, field
from typing import Any, FrozenSet, Iterable, Mapping, Optional

from . import parameters as P

GOALS = ("maintenance", "hypertrophy", "strength", "general_fitness", "fat_loss")
EXPERIENCE_LEVELS = ("beginner", "intermediate", "advanced")

# Every goal value used anywhere in NosiFit (registration, OAuth profile,
# profile editor, onboarding) mapped to the model vocabulary.
GOAL_ALIASES = {
    "maintenance": "maintenance",
    "maintain": "maintenance",
    "hypertrophy": "hypertrophy",
    "muscle_gain": "hypertrophy",
    "gain": "hypertrophy",
    "recomposition": "hypertrophy",
    "strength": "strength",
    "general_fitness": "general_fitness",
    "performance": "general_fitness",
    "endurance": "general_fitness",
    "fat_loss": "fat_loss",
    "lose": "fat_loss",
    "weight_loss": "fat_loss",
}

EXPERIENCE_ALIASES = {
    "beginner": "beginner",
    "novice": "beginner",
    "початківець": "beginner",
    "початковий": "beginner",
    "intermediate": "intermediate",
    "середній": "intermediate",
    "advanced": "advanced",
    "elite": "advanced",
    "досвідчений": "advanced",
    "просунутий": "advanced",
}

# Questionnaire body regions -> catalog muscle slugs.
REGION_MUSCLES = {
    "chest": ("chest",),
    "back": ("lats", "upper-back", "traps", "lower-back"),
    "shoulders": ("shoulders",),
    "arms": ("biceps", "triceps", "forearms"),
    "legs": ("quads", "hamstrings", "glutes", "adductors", "calves"),
    "glutes": ("glutes",),
    "core": ("core", "abs", "obliques"),
    "lower_back": ("lower-back",),
}

# Onboarding focus regions (focus_upper / focus_lower / focus_core).
FOCUS_REGIONS = {
    "upper": ("chest", "lats", "upper-back", "traps", "shoulders", "biceps", "triceps", "forearms", "neck"),
    "lower": ("quads", "hamstrings", "glutes", "adductors", "calves", "hip-flexors"),
    "core": ("abs", "obliques", "core", "lower-back"),
}

GYM_LOCATIONS = ("gym",)


def normalize_goal(value: Any) -> str:
    key = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    return GOAL_ALIASES.get(key, "general_fitness")


def normalize_experience(value: Any) -> str:
    key = str(value or "").strip().lower()
    return EXPERIENCE_ALIASES.get(key, "beginner")


def weak_muscles(points: Any) -> FrozenSet[str]:
    if not points:
        return frozenset()
    if isinstance(points, str):
        points = points.split(",")
    if not isinstance(points, (list, tuple, set, frozenset)):
        return frozenset()
    muscles = set()
    for point in points:
        key = str(point).strip().lower()
        if key:
            muscles.update(REGION_MUSCLES.get(key, (key.replace("_", "-"),)))
    return frozenset(muscles)


def focus_by_muscle(upper: Any = None, lower: Any = None, core: Any = None) -> Mapping[str, float]:
    result = {}
    for region, value in (("upper", upper), ("lower", lower), ("core", core)):
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        for muscle in FOCUS_REGIONS[region]:
            result[muscle] = number
    return result


@dataclass(frozen=True)
class TrainingContext:
    goal: str = "general_fitness"
    experience: str = "beginner"
    workouts_per_week: int = P.DEFAULT_WORKOUTS_PER_WEEK
    weak_muscles: FrozenSet[str] = frozenset()
    focus: Mapping[str, float] = field(default_factory=dict, compare=False, hash=False)
    # None = no restriction (gym, or nothing known about a gym user).
    available_equipment: Optional[FrozenSet[str]] = None
    body_weight_kg: Optional[float] = None


def build_context(
    user: Any,
    profile: Any = None,
    training_goals: Any = None,
    equipment_slugs: Optional[Iterable[str]] = None,
) -> TrainingContext:
    """Context from ORM-like objects.

    The profile is the source of truth. The legacy User columns are read only
    when no profile exists: the current forms never fill them, so with a
    profile their values would only be column defaults, not user choices."""
    source = profile if profile is not None else user

    def pick(name: str) -> Any:
        value = getattr(source, name, None) if source is not None else None
        return None if value in (None, "") else value

    goal_value = getattr(training_goals, "primary_goal", None) or pick("goal")
    try:
        workouts = int(pick("workouts_per_week") or P.DEFAULT_WORKOUTS_PER_WEEK)
    except (TypeError, ValueError):
        workouts = P.DEFAULT_WORKOUTS_PER_WEEK
    workouts = max(1, min(workouts, P.MAX_WORKOUTS_PER_WEEK_INPUT))

    location = str(pick("training_location") or pick("environment") or "").strip().lower()

    if equipment_slugs:
        available = frozenset(str(slug).strip().lower() for slug in equipment_slugs) | {"bodyweight"}
    elif location in GYM_LOCATIONS:
        available = None
    else:
        # Nothing configured outside a gym: only equipment-free exercises.
        available = frozenset({"bodyweight"})

    try:
        body_weight = float(pick("weight")) if pick("weight") else None
    except (TypeError, ValueError):
        body_weight = None

    return TrainingContext(
        goal=normalize_goal(goal_value),
        experience=normalize_experience(pick("experience")),
        workouts_per_week=workouts,
        weak_muscles=weak_muscles(getattr(user, "weak_points", None)),
        focus=focus_by_muscle(
            getattr(training_goals, "focus_upper", None),
            getattr(training_goals, "focus_lower", None),
            getattr(training_goals, "focus_core", None),
        ),
        available_equipment=available,
        body_weight_kg=body_weight,
    )
