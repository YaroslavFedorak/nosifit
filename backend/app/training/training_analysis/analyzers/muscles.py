from datetime import date, timedelta
from typing import Dict, List, Any

from backend.app.services.training.load.service import TrainingLoadService
from backend.app.training.models.exercise import Exercise
from backend.app.training.training_analysis.dto import MuscleResult

WEAK_RATIO = 0.70
OVERLOADED_RATIO = 1.35


def _exercise_load(
    session_exercise: Any,
    exercise: Exercise,
    user_weight: float,
) -> float:
    """Internal training load of one logged exercise.

    This is an analytics metric computed by the load engine in each
    exercise's own unit (sets x reps or sets x seconds); it never converts
    seconds into repetitions or the other way round.
    """
    result = TrainingLoadService.compute_exercise_load(
        session_exercise=session_exercise,
        exercise=exercise,
        capacity={"weight": user_weight},
    )

    return float(result.get("internal_load", 0.0))


def _add_exercise_muscles(
    totals: Dict[str, float],
    session_exercise: Any,
    user_weight: float,
) -> None:
    exercise = Exercise.query.get(session_exercise.exercise_id)

    if not exercise:
        return

    muscles = list(exercise.muscles_primary or []) + list(
        exercise.muscles_secondary or []
    )

    muscles = [str(muscle).strip().lower() for muscle in muscles if str(muscle).strip()]

    if not muscles:
        return

    volume = _exercise_load(session_exercise, exercise, user_weight)

    if volume <= 0:
        return

    share = volume / len(muscles)

    for muscle in muscles:
        totals[muscle] = totals.get(muscle, 0.0) + share


def _add_stored_muscle_loads(
    totals: Dict[str, float],
    session: Any,
) -> bool:
    muscle_loads = session.muscle_loads or {}

    if not isinstance(muscle_loads, dict) or not muscle_loads:
        return False

    added = False

    for muscle, value in muscle_loads.items():
        muscle_key = str(muscle).strip().lower()

        if not muscle_key:
            continue

        try:
            numeric_value = float(value or 0.0)
        except (TypeError, ValueError):
            continue

        if numeric_value <= 0:
            continue

        totals[muscle_key] = totals.get(muscle_key, 0.0) + numeric_value
        added = True

    return added


def _calculate_totals(window: List[Any], user_weight: float) -> Dict[str, float]:
    totals: Dict[str, float] = {}

    for session in window:
        has_stored_load = _add_stored_muscle_loads(
            totals,
            session,
        )

        if has_stored_load:
            continue

        for session_exercise in session.exercises or []:
            _add_exercise_muscles(
                totals,
                session_exercise,
                user_weight,
            )

    return {muscle: round(value, 3) for muscle, value in totals.items() if value > 0}


def _median(values: List[float]) -> float:
    ordered = sorted(values)

    if not ordered:
        return 0.0

    middle = len(ordered) // 2

    if len(ordered) % 2:
        return ordered[middle]

    return (ordered[middle - 1] + ordered[middle]) / 2.0


def analyse_muscles(
    sessions: List,
    target_day: date,
    days: int = 14,
    user_weight: float = 70.0,
) -> MuscleResult:
    start = target_day - timedelta(days=days)

    window = [
        session
        for session in sessions
        if session.started_at and start <= session.started_at.date() <= target_day
    ]

    totals = _calculate_totals(window, user_weight)

    if not totals:
        return {
            "weak": [],
            "overloaded": [],
            "balanced": [],
            "totals": {},
            "balance_ratio": {},
            "message": "no muscle data",
        }

    reference = _median(list(totals.values()))

    if reference <= 0:
        balanced = sorted(totals.keys())

        return {
            "weak": [],
            "overloaded": [],
            "balanced": balanced,
            "totals": totals,
            "balance_ratio": {muscle: 1.0 for muscle in totals},
            "message": "muscle balance analysed",
        }

    weak: List[str] = []
    overloaded: List[str] = []
    balanced: List[str] = []
    ratios: Dict[str, float] = {}

    for muscle, value in totals.items():
        ratio = value / reference
        ratios[muscle] = round(ratio, 3)

        if ratio < WEAK_RATIO:
            weak.append(muscle)
        elif ratio > OVERLOADED_RATIO:
            overloaded.append(muscle)
        else:
            balanced.append(muscle)

    weak.sort(key=lambda muscle: ratios[muscle])
    overloaded.sort(key=lambda muscle: ratios[muscle], reverse=True)
    balanced.sort(key=lambda muscle: abs(ratios[muscle] - 1.0))

    weak = weak[:4]
    overloaded = overloaded[:3]
    balanced = balanced[:3]

    return {
        "weak": weak,
        "overloaded": overloaded,
        "balanced": balanced,
        "totals": totals,
        "balance_ratio": ratios,
        "message": "muscle balance analysed",
    }

