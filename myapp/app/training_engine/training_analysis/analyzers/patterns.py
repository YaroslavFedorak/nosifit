from datetime import date, timedelta
from typing import Any, Dict, List, Mapping

from myapp.app.training_engine.training_analysis.analyzers.utils import movement_pattern
from myapp.app.training_engine.training_analysis.constants import (
    PATTERN_HIGH_THRESHOLD,
    PATTERN_LOW_THRESHOLD,
)
from myapp.app.training_engine.training_analysis.dto import PatternResult
from myapp.app.services.training.load.service import TrainingLoadService


def analyse_patterns(
    sessions: List,
    target_day: date,
    exercise_map: Mapping[object, object],
    user: Any,
    days: int = 14,
) -> PatternResult:
    start = target_day - timedelta(days=days)

    user_weight = float(getattr(user, "weight", 70) or 70)

    window = [
        session
        for session in sessions
        if session.started_at and start <= session.started_at.date() <= target_day
    ]

    pattern_loads: Dict[str, float] = {}

    for session in window:
        internal = float(getattr(session, "internal_load", 0) or 0)
        if internal <= 0:
            continue

        exercise_loads = []
        total_exercise_load = 0.0

        for session_exercise in session.exercises or []:
            exercise = exercise_map.get(session_exercise.exercise_id)
            if not exercise:
                continue

            exercise_load_data = TrainingLoadService.compute_exercise_load(
                session_exercise=session_exercise,
                exercise=exercise,
                capacity={"weight": user_weight},
            )

            internal_load = float(exercise_load_data.get("internal_load", 0))
            if internal_load <= 0:
                continue

            exercise_loads.append((exercise, internal_load))
            total_exercise_load += internal_load

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

    weak_patterns = []
    overloaded_patterns = []

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
