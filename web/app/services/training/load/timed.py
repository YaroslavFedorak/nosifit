from .constants import (
    GLOBAL_LOAD_SCALE,
    TIME_BASE_SECONDS,
    TIME_BASED_EXERCISES,
    TIME_EXPONENT,
    TIME_SCALE,
)

from .factors import (
    difficulty_factor,
    effective_load,
    exercise_load_factor,
    movement_factor,
    risk_factor,
    rpe_factor,
)

from .parsing import (
    clamp,
    parse_float,
    parse_int,
    parse_reps,
)


def is_time_based_exercise(exercise):
    slug = (
        getattr(
            exercise,
            "slug",
            None,
        )
        or ""
    ).lower()

    name = (
        getattr(
            exercise,
            "name",
            None,
        )
        or ""
    ).lower()

    normalized = slug.replace("_", "-").replace(" ", "-")

    return (
        normalized in TIME_BASED_EXERCISES
        or "plank" in name
        or "wall sit" in name
        or "dead hang" in name
    )


def is_timed_exercise(exercise):
    return is_time_based_exercise(exercise)


def compute_timed_load(
    exercise,
    sets,
    duration,
    additional_load,
    user_weight,
    capacity=1.0,
    rpe=7.0,
):
    sets = parse_int(sets)
    duration = parse_reps(duration)
    additional_load = parse_float(additional_load)

    if sets <= 0 or duration <= 0:
        return {
            "sets": sets,
            "reps": duration,
            "seconds": duration,
            "load": 0.0,
            "additional_load": additional_load,
            "effective_load": 0.0,
            "volume": 0.0,
            "external_load": 0.0,
            "internal_load": 0.0,
        }

    effective = effective_load(
        exercise,
        user_weight,
        additional_load,
    )

    normalized_time = max(
        duration / TIME_BASE_SECONDS,
        0.1,
    )

    volume = sets * normalized_time**TIME_EXPONENT * TIME_SCALE

    load_factor = exercise_load_factor(
        exercise,
        user_weight,
        additional_load,
    )

    movement = movement_factor(exercise)
    difficulty = difficulty_factor(exercise)
    risk = risk_factor(exercise)
    rpe_multiplier = rpe_factor(rpe)

    external_load = (
        volume * load_factor * movement * difficulty * risk * GLOBAL_LOAD_SCALE
    )

    internal_load = (
        external_load
        * rpe_multiplier
        * clamp(
            capacity,
            0.85,
            1.15,
        )
    )

    return {
        "sets": sets,
        "reps": duration,
        "seconds": duration,
        "load": effective,
        "additional_load": additional_load,
        "effective_load": effective,
        "volume": volume,
        "external_load": external_load,
        "internal_load": internal_load,
    }


def calculate_timed_load(
    exercise,
    user_weight=70.0,
):
    sets = getattr(
        exercise,
        "sets",
        0,
    )

    duration = getattr(
        exercise,
        "reps",
        0,
    )

    additional_load = getattr(
        exercise,
        "weight",
        0,
    )

    result = compute_timed_load(
        exercise=exercise,
        sets=sets,
        duration=duration,
        additional_load=additional_load,
        user_weight=user_weight,
    )

    return result["internal_load"]
