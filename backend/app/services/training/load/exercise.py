from backend.app.training.exercises.prescription import is_duration_exercise

from .factors import (
    difficulty_factor,
    effective_load,
    exercise_load_factor,
    movement_factor,
    risk_factor,
    rpe_factor,
)

from .parsing import (
    parse_float,
    parse_reps,
)
from .timed import compute_timed_load


def calculate_exercise_load(
    exercise,
    user_weight=70.0,
    sets=None,
    reps=None,
    additional_weight=None,
    capacity=1.0,
    rpe=7.0,
):
    sets = parse_reps(sets)

    reps = parse_reps(reps)

    additional_weight = parse_float(additional_weight)

    if sets <= 0 or reps <= 0:
        return {
            "sets": sets,
            "reps": reps,
            "load": 0.0,
            "effective_load": 0.0,
            "volume": 0.0,
            "external_load": 0.0,
            "internal_load": 0.0,
        }

    effective = effective_load(
        exercise,
        user_weight,
        additional_weight,
    )

    volume = sets * reps

    load_factor = exercise_load_factor(
        exercise,
        user_weight,
        additional_weight,
    )

    movement = movement_factor(exercise)
    difficulty = difficulty_factor(exercise)
    risk = risk_factor(exercise)
    rpe_multiplier = rpe_factor(rpe)

    external_load = volume * load_factor * movement * difficulty * risk

    internal_load = (
        external_load
        * rpe_multiplier
        * max(
            0.85,
            min(
                float(capacity),
                1.15,
            ),
        )
    )

    return {
        "sets": sets,
        "reps": reps,
        "load": effective,
        "effective_load": effective,
        "volume": volume,
        "external_load": external_load,
        "internal_load": internal_load,
    }



def calculate_measured_load(
    exercise,
    user_weight=70.0,
    sets=0,
    reps=None,
    duration_sec=None,
    additional_weight=None,
    capacity=1.0,
    rpe=7.0,
):
    """Load of one exercise: sets x reps for repetition exercises,
    sets x seconds for duration exercises."""
    if is_duration_exercise(exercise):
        result = compute_timed_load(
            exercise=exercise,
            sets=sets,
            duration=duration_sec,
            additional_load=additional_weight,
            user_weight=user_weight,
            capacity=capacity,
            rpe=rpe,
        )
        result["measurement_type"] = "duration"
        return result

    result = calculate_exercise_load(
        exercise=exercise,
        user_weight=user_weight,
        sets=sets,
        reps=reps,
        additional_weight=additional_weight,
        capacity=capacity,
        rpe=rpe,
    )
    result["measurement_type"] = "reps"
    return result
