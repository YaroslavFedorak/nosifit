from typing import Mapping, List, Dict
from datetime import date, timedelta

from myapp.app.training_engine.training_analysis.dto import PatternResult
from myapp.app.training_engine.training_analysis.constants import (
    PATTERN_LOW_THRESHOLD,
    PATTERN_HIGH_THRESHOLD,
)
from myapp.app.training_engine.training_analysis.analyzers.utils import (
    movement_pattern,
)
from myapp.app.services.training.load_index_service import (
    _compute_exercise_load,
)


def analyse_patterns(
    sessions: List,
    target_day: date,
    exercise_map: Mapping[object, object],
    user_weight: float,
    days: int = 14,
) -> PatternResult:
    start = target_day - timedelta(days=days)

    window = [
        session
        for session in sessions
        if session.started_at and start <= session.started_at.date() <= target_day
    ]

    pattern_loads: Dict[str, float] = {}

    for session in window:
        internal = float(getattr(session, "internal_load", 0.0) or 0.0)

        if internal <= 0:
            internal = 1.0

        total_exercise_load = 0.0
        exercise_loads = []

        for session_exercise in session.exercises or []:
            exercise = exercise_map.get(session_exercise.exercise_id)

            if not exercise:
                continue

            sets = session_exercise.sets_done or session_exercise.sets_planned or 0

            reps = session_exercise.reps_done or session_exercise.reps_planned or "0"

            load = (
                session_exercise.load_done
                if session_exercise.load_done is not None
                else session_exercise.load_planned or 0
            )

            exercise_load = _compute_exercise_load(
                exercise,
                sets,
                reps,
                load,
                user_weight,
            )

            if exercise_load <= 0:
                continue

            exercise_loads.append((exercise, exercise_load))
            total_exercise_load += exercise_load

        if total_exercise_load <= 0:
            continue

        for exercise, exercise_load in exercise_loads:
            share = exercise_load / total_exercise_load
            pattern = movement_pattern(exercise)

            pattern_loads[pattern] = pattern_loads.get(pattern, 0.0) + share * internal

    if not pattern_loads:
        return {
            "weak_patterns": [],
            "overloaded_patterns": [],
            "pattern_loads": {},
            "message": "no pattern data",
        }

    total = sum(pattern_loads.values())

    weak_patterns: List[str] = []
    overloaded_patterns: List[str] = []

    for pattern, value in pattern_loads.items():
        ratio = value / total if total > 0 else 0.0

        if ratio < PATTERN_LOW_THRESHOLD:
            weak_patterns.append(pattern)
        elif ratio > PATTERN_HIGH_THRESHOLD:
            overloaded_patterns.append(pattern)

    return {
        "weak_patterns": weak_patterns,
        "overloaded_patterns": overloaded_patterns,
        "pattern_loads": pattern_loads,
        "message": "movement patterns analysed",
    }
