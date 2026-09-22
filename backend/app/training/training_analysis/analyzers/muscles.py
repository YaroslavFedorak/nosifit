from datetime import date, timedelta
from typing import Dict, List, Any

from backend.app.training.models.exercise import Exercise
from backend.app.training.training_analysis.dto import MuscleResult

WEAK_RATIO = 0.70
OVERLOADED_RATIO = 1.35


def _parse_reps(value: Any) -> float:
    if value is None:
        return 1.0

    if isinstance(value, (int, float)):
        return max(float(value), 1.0)

    text = str(value).strip()

    if not text:
        return 1.0

    if "-" in text:
        parts = text.split("-", 1)

        try:
            low = float(parts[0].strip())
            high = float(parts[1].strip())
            return max((low + high) / 2.0, 1.0)
        except (TypeError, ValueError):
            return 1.0

    try:
        return max(float(text), 1.0)
    except (TypeError, ValueError):
        return 1.0


def _exercise_volume(session_exercise: Any) -> float:
    sets = session_exercise.sets_done or session_exercise.sets_planned or 0
    reps = session_exercise.reps_done or session_exercise.reps_planned or 1
    load = session_exercise.load_done or session_exercise.load_planned or 0

    try:
        sets_value = max(float(sets), 0.0)
    except (TypeError, ValueError):
        sets_value = 0.0

    reps_value = _parse_reps(reps)

    try:
        load_value = max(float(load), 0.0)
    except (TypeError, ValueError):
        load_value = 0.0

    if sets_value <= 0:
        return 0.0

    base_volume = sets_value * reps_value

    if load_value > 0:
        return base_volume * (1.0 + min(load_value / 100.0, 2.0))

    return base_volume


def _add_exercise_muscles(
    totals: Dict[str, float],
    session_exercise: Any,
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

    volume = _exercise_volume(session_exercise)

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


def _calculate_totals(window: List[Any]) -> Dict[str, float]:
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
) -> MuscleResult:
    start = target_day - timedelta(days=days)

    window = [
        session
        for session in sessions
        if session.started_at and start <= session.started_at.date() <= target_day
    ]

    totals = _calculate_totals(window)

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

