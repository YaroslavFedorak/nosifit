from backend.app.training.exercises.catalog import LOAD_BODYWEIGHT

from .constants import DEFAULT_BODYWEIGHT_RATIO, MOVEMENT_FACTORS
from .parsing import parse_float, normalize_name


def is_bodyweight_exercise(exercise):
    load_type = getattr(exercise, "load_type", None)

    if load_type:
        return load_type == LOAD_BODYWEIGHT

    equipment = getattr(exercise, "equipment", None) or []

    if isinstance(equipment, str):
        equipment = [equipment]

    return "bodyweight" in {normalize_name(item) for item in equipment}


def bodyweight_ratio(exercise):
    ratio = parse_float(getattr(exercise, "bodyweight_ratio", None))

    return ratio if ratio > 0 else DEFAULT_BODYWEIGHT_RATIO


def bodyweight_load(exercise, user_weight):
    return user_weight * bodyweight_ratio(exercise)


def effective_load(
    exercise,
    user_weight,
    additional_load,
):
    additional_load = max(
        parse_float(additional_load),
        0.0,
    )

    if is_bodyweight_exercise(exercise):
        return (
            bodyweight_load(
                exercise,
                user_weight,
            )
            + additional_load
        )

    return additional_load


def exercise_load_factor(
    exercise,
    user_weight,
    additional_load,
):
    additional_load = max(
        parse_float(additional_load),
        0.0,
    )

    if is_bodyweight_exercise(exercise):
        ratio = bodyweight_ratio(exercise)

        factor = 0.65 + 0.45 * ratio

        if user_weight > 0:
            additional_ratio = additional_load / user_weight

            factor += (
                min(
                    additional_ratio,
                    0.40,
                )
                * 0.35
            )

        return min(
            factor,
            1.20,
        )

    max_additional_load = parse_float(
        getattr(
            exercise,
            "max_additional_load_kg",
            0,
        )
    )

    if additional_load <= 0:
        return 0.55

    if max_additional_load <= 0:
        return 0.75

    ratio = min(
        additional_load / max_additional_load,
        1.25,
    )

    return min(
        0.55 + ratio * 0.60,
        1.30,
    )


def movement_factor(exercise):
    pattern = normalize_name(
        getattr(
            exercise,
            "movement_pattern",
            None,
        )
    )

    return MOVEMENT_FACTORS.get(
        pattern,
        1.00,
    )


def difficulty_factor(exercise):
    difficulty = parse_float(
        getattr(
            exercise,
            "difficulty",
            1,
        )
    )

    difficulty = max(
        1.0,
        min(difficulty, 5.0),
    )

    return 0.96 + difficulty * 0.04


def risk_factor(exercise):
    risk = parse_float(
        getattr(
            exercise,
            "risk_level",
            1,
        )
    )

    risk = max(
        0.0,
        min(risk, 5.0),
    )

    return 1.0 + risk * 0.02


def rpe_factor(rpe):
    if rpe is None:
        return 1.0

    value = parse_float(rpe)

    value = max(
        1.0,
        min(value, 10.0),
    )

    return 0.85 + (value / 10.0) * 0.30


def effort_factor(reps):
    reps = max(
        float(reps),
        0.0,
    )

    return (
        0.85
        + min(
            reps / 30.0,
            1.0,
        )
        * 0.15
    )

