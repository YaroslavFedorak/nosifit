from .constants import (
    BODYWEIGHT_FACTOR,
    BODYWEIGHT_RATIOS,
    MOVEMENT_FACTORS,
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
    normalize_name,
    parse_float,
    parse_reps,
)


def get_movement_factor(exercise):
    movement = getattr(
        exercise,
        "movement_pattern",
        None,
    )

    movement = normalize_name(movement)

    if movement in MOVEMENT_FACTORS:
        return MOVEMENT_FACTORS[movement]

    name = normalize_name(getattr(exercise, "name", ""))

    if any(
        word in name
        for word in (
            "stretch",
            "mobility",
            "cat-cow",
            "thread-the-needle",
            "розтяг",
            "кішка-корова",
        )
    ):
        return MOVEMENT_FACTORS["mobility"]

    if any(
        word in name
        for word in (
            "plank",
            "dead-bug",
            "deadbug",
            "crunch",
            "bicycle",
            "велосипед",
            "планка",
        )
    ):
        return MOVEMENT_FACTORS["core"]

    if any(
        word in name
        for word in (
            "squat",
            "lunge",
            "step-up",
            "glute",
            "kickback",
            "присід",
            "випад",
            "відведення-ноги",
        )
    ):
        return MOVEMENT_FACTORS["lower"]

    if any(
        word in name
        for word in (
            "row",
            "pull-up",
            "pulldown",
            "curl",
            "тяга",
            "підтяг",
        )
    ):
        return MOVEMENT_FACTORS["pull"]

    if any(
        word in name
        for word in (
            "push-up",
            "pushup",
            "bench-press",
            "press",
            "dip",
            "віджим",
            "жим",
        )
    ):
        return MOVEMENT_FACTORS["push"]

    if any(
        word in name
        for word in (
            "burpee",
            "mountain-climber",
            "bear-crawl",
        )
    ):
        return MOVEMENT_FACTORS["full_body"]

    return MOVEMENT_FACTORS["accessory"]


def get_bodyweight_ratio(exercise):
    slug = normalize_name(getattr(exercise, "slug", ""))

    name = normalize_name(getattr(exercise, "name", ""))

    if slug in BODYWEIGHT_RATIOS:
        return BODYWEIGHT_RATIOS[slug]

    if name in BODYWEIGHT_RATIOS:
        return BODYWEIGHT_RATIOS[name]

    for key, ratio in BODYWEIGHT_RATIOS.items():
        if key in slug or key in name:
            return ratio

    return BODYWEIGHT_FACTOR


def calculate_exercise_load(
    exercise,
    user_weight=70.0,
    sets=None,
    reps=None,
    additional_weight=None,
    capacity=1.0,
    rpe=7.0,
):
    sets = parse_reps(getattr(exercise, "sets", 0) if sets is None else sets)

    reps = parse_reps(getattr(exercise, "reps", 0) if reps is None else reps)

    additional_weight = parse_float(
        getattr(exercise, "weight", 0)
        if additional_weight is None
        else additional_weight
    )

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
