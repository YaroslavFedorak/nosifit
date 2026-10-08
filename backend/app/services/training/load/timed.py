from .constants import (
    GLOBAL_LOAD_SCALE,
    TIME_BASE_SECONDS,
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
    parse_seconds,
)


def compute_timed_load(
    exercise,
    sets,
    duration,
    additional_load,
    user_weight,
    capacity=1.0,
    rpe=7.0,
):
    """Internal load of a duration exercise; ``duration`` is seconds per set.

    ``volume`` here is time volume, sets x (seconds / TIME_BASE_SECONDS) **
    TIME_EXPONENT, in load units. It is not a repetition count.
    """
    sets = parse_int(sets)
    duration = parse_seconds(duration)
    additional_load = parse_float(additional_load)

    if sets <= 0 or duration <= 0:
        return {
            "sets": sets,
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
        "seconds": duration,
        "load": effective,
        "additional_load": additional_load,
        "effective_load": effective,
        "volume": volume,
        "external_load": external_load,
        "internal_load": internal_load,
    }
