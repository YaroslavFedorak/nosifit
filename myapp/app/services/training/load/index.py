from datetime import date

from myapp.app.training_engine.models.fatigue_state import (
    FatigueState,
)

from .constants import (
    CHRONIC_WINDOW_DAYS,
    REFERENCE_CAPACITY_WEIGHT,
    REFERENCE_HISTORY_WEIGHT,
)

from .physiology import (
    build_capacity,
    reference_capacity,
)

from .session import (
    build_daily_loads,
    calculate_chronic_mean,
)


def compute_fatigue_factor(
    user,
    daily_loads,
    target_day,
):
    fatigue = getattr(
        user,
        "fatigue_state",
        None,
    )

    factor = 1.0

    if isinstance(fatigue, FatigueState):
        stress = (
            getattr(
                fatigue,
                "stress",
                0,
            )
            or 0
        )

        soreness = (
            getattr(
                fatigue,
                "soreness",
                0,
            )
            or 0
        )

        sleep = (
            getattr(
                fatigue,
                "sleep",
                7,
            )
            or 7
        )

        factor *= 1.0 + (stress + soreness) * 0.02

        factor *= 1.0 - max(0, 8 - sleep) * 0.015

    recent_days = 0

    for offset in range(1, 4):
        day = target_day - __import__("datetime").timedelta(days=offset)

        if (
            daily_loads.get(
                day,
                0.0,
            )
            > 0
        ):
            recent_days += 1

    factor *= 1.0 + recent_days * 0.03

    return max(
        0.7,
        min(factor, 1.3),
    )


def get_level(
    user,
):
    value = (
        getattr(user, "level", None)
        or getattr(user, "experience", None)
        or "intermediate"
    )

    value = str(value).strip().lower()

    mapping = {
        "початківець": "beginner",
        "початковий": "beginner",
        "beginner": "beginner",
        "novice": "beginner",
        "середній": "intermediate",
        "intermediate": "intermediate",
        "досвідчений": "advanced",
        "просунутий": "advanced",
        "advanced": "advanced",
        "елітний": "elite",
        "elite": "elite",
    }

    return mapping.get(
        value,
        "intermediate",
    )


def calculate_reference_load(
    user,
    chronic_mean,
):
    capacity = build_capacity(user)

    capacity_reference = reference_capacity(user)

    history_reference = chronic_mean

    reference_load = (
        REFERENCE_CAPACITY_WEIGHT * capacity_reference
        + REFERENCE_HISTORY_WEIGHT * history_reference
    )

    minimum_reference = {
        "beginner": 70.0,
        "intermediate": 90.0,
        "advanced": 110.0,
        "elite": 120.0,
    }.get(
        get_level(user),
        90.0,
    )

    return max(
        reference_load,
        minimum_reference,
    )


def compute_daily_load_index(
    user,
    sessions,
    target_day=None,
):
    target_day = target_day or date.today()

    daily_loads = build_daily_loads(
        sessions,
        user,
    )

    load_today = daily_loads.get(
        target_day,
        0.0,
    )

    if load_today <= 0:
        return {
            "percent": 0,
            "raw_percent": 0.0,
            "level": 0,
            "load_today": 0.0,
            "reference_load": 0.0,
            "capacity": 0.0,
            "chronic_mean": 0.0,
            "fatigue_factor": 1.0,
        }

    chronic_mean = calculate_chronic_mean(
        daily_loads,
        target_day,
        CHRONIC_WINDOW_DAYS,
    )

    capacity = build_capacity(user)

    reference_load = calculate_reference_load(
        user,
        chronic_mean,
    )

    fatigue_factor = compute_fatigue_factor(
        user,
        daily_loads,
        target_day,
    )

    adjusted_load = load_today * fatigue_factor

    raw_percent = (adjusted_load / max(reference_load, 1.0)) * 100.0

    percent = int(
        max(
            0.0,
            min(
                raw_percent,
                150.0,
            ),
        )
    )

    if percent < 20:
        level = 0
    elif percent < 40:
        level = 1
    elif percent < 60:
        level = 2
    elif percent < 80:
        level = 3
    else:
        level = 4

    return {
        "percent": percent,
        "raw_percent": float(raw_percent),
        "level": level,
        "load_today": float(load_today),
        "reference_load": float(reference_load),
        "capacity": float(capacity.capacity),
        "chronic_mean": float(chronic_mean),
        "fatigue_factor": float(fatigue_factor),
    }
