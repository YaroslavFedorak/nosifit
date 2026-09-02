from .constants import BODYWEIGHT_RATIO
from .parsing import parse_float, normalize_name


def is_bodyweight_exercise(exercise):
    equipment = getattr(exercise, "equipment", None) or []

    if isinstance(equipment, str):
        equipment = [equipment]

    normalized = {normalize_name(item) for item in equipment}

    slug = normalize_name(getattr(exercise, "slug", None))

    name = normalize_name(getattr(exercise, "name", None))

    return (
        "bodyweight" in normalized
        or slug in BODYWEIGHT_RATIO
        or name in BODYWEIGHT_RATIO
    )


def bodyweight_ratio(exercise):
    slug = normalize_name(getattr(exercise, "slug", None))

    name = normalize_name(getattr(exercise, "name", None))

    if slug in BODYWEIGHT_RATIO:
        return BODYWEIGHT_RATIO[slug]

    if name in BODYWEIGHT_RATIO:
        return BODYWEIGHT_RATIO[name]

    for key, ratio in BODYWEIGHT_RATIO.items():
        if key in slug or key in name:
            return ratio

    return 0.50


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

    values = {
        "upper-body": 1.00,
        "lower-body": 1.10,
        "core": 0.90,
        "full-body": 1.15,
        "mobility": 0.30,
        "push": 1.00,
        "pull": 1.05,
        "hinge": 1.08,
        "squat": 1.08,
        "accessory": 0.80,
    }

    return values.get(
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
