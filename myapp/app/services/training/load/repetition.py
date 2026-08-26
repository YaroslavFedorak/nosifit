from .constants import BODYWEIGHT_RATIO, GLOBAL_LOAD_SCALE
from .factors import (
    difficulty_factor,
    muscle_factor,
    movement_factor,
    rpe_factor,
)
from .parsing import clamp, parse_float, parse_reps


def bodyweight_ratio(exercise):
    slug = (getattr(exercise, "slug", None) or "").lower()

    if slug in BODYWEIGHT_RATIO:
        return BODYWEIGHT_RATIO[slug]

    pattern = (getattr(exercise, "movement_pattern", None) or "").lower()

    if "push" in pattern:
        return 0.55

    if "pull" in pattern:
        return 0.80

    if "lower" in pattern:
        return 0.65

    if "core" in pattern:
        return 0.30

    return 0.45


def effective_load(exercise, load, user_weight):
    load = parse_float(load)

    if load > 0:
        return load

    return max(user_weight, 1.0) * bodyweight_ratio(exercise)


def repetition_volume(sets, reps):
    sets = max(parse_float(sets), 0.0)
    reps = max(parse_reps(reps), 0.0)

    return sets * (reps**0.75)


def calculate_repetition_load(
    exercise,
    sets,
    reps,
    load,
    user_weight,
    rpe=None,
):
    effective = effective_load(
        exercise,
        load,
        user_weight,
    )

    volume = repetition_volume(
        sets,
        reps,
    )

    intensity = clamp(
        effective / max(user_weight, 1.0),
        0.25,
        2.0,
    )

    return (
        volume
        * effective
        * intensity
        * movement_factor(exercise)
        * difficulty_factor(exercise)
        * muscle_factor(exercise)
        * rpe_factor(rpe)
        * GLOBAL_LOAD_SCALE
    )
