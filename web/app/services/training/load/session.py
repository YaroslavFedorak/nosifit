from datetime import timedelta

from .constants import MAX_DURATION_BONUS
from .exercise import calculate_exercise_load
from .timed import (
    calculate_timed_load,
    is_timed_exercise,
)
from .parsing import parse_float


def get_session_exercise_value(
    session_exercise,
    done_name,
    planned_name,
    default=0,
):
    value = getattr(
        session_exercise,
        done_name,
        None,
    )

    if value is not None:
        return value

    return getattr(
        session_exercise,
        planned_name,
        default,
    )


def calculate_session_load(session, user):
    user_weight = parse_float(
        getattr(
            user,
            "weight",
            70.0,
        ),
        70.0,
    )

    exercises = (
        getattr(
            session,
            "exercises",
            [],
        )
        or []
    )

    total_load = 0.0

    for session_exercise in exercises:
        from web.app.training_engine.models.exercise import Exercise

        exercise = Exercise.query.get(session_exercise.exercise_id)

        if not exercise:
            continue

        sets = get_session_exercise_value(
            session_exercise,
            "sets_done",
            "sets_planned",
        )

        reps = get_session_exercise_value(
            session_exercise,
            "reps_done",
            "reps_planned",
        )

        weight = get_session_exercise_value(
            session_exercise,
            "load_done",
            "load_planned",
        )

        rpe = getattr(
            session_exercise,
            "rpe",
            None,
        )

        if is_timed_exercise(exercise):
            result = calculate_timed_load(
                exercise,
                user_weight,
            )

            total_load += result

            continue

        result = calculate_exercise_load(
            exercise=exercise,
            user_weight=user_weight,
            sets=sets,
            reps=reps,
            additional_weight=weight,
            rpe=7.0 if rpe is None else rpe,
        )

        total_load += result["internal_load"]

    duration = getattr(
        session,
        "duration",
        None,
    )

    if duration is None:
        duration = getattr(
            session,
            "duration_minutes",
            0,
        )

    try:
        duration = float(duration or 0)
    except (TypeError, ValueError):
        duration = 0.0

    duration_bonus = min(
        (duration / 120.0) * MAX_DURATION_BONUS,
        MAX_DURATION_BONUS,
    )

    total_load *= 1.0 + duration_bonus

    return round(
        max(total_load, 0.0),
        2,
    )


def build_daily_loads(sessions, user):
    daily_loads = {}

    for session in sessions:
        session_date = getattr(
            session,
            "started_at",
            None,
        )

        if session_date is None:
            session_date = getattr(
                session,
                "date",
                None,
            )

        if session_date is None:
            session_date = getattr(
                session,
                "created_at",
                None,
            )

        if session_date is None:
            continue

        day = session_date.date() if hasattr(session_date, "date") else session_date

        load = calculate_session_load(
            session,
            user,
        )

        daily_loads[day] = daily_loads.get(day, 0.0) + load

    return daily_loads


def calculate_chronic_mean(
    daily_loads,
    target_day,
    window_days=14,
):
    if not daily_loads:
        return 0.0

    total = 0.0

    for offset in range(window_days):
        day = target_day - timedelta(days=offset)

        total += daily_loads.get(
            day,
            0.0,
        )

    return total / window_days
