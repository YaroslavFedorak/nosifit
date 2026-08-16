from typing import Mapping, List, Dict
from datetime import date, timedelta
from myapp.app.training_engine.training_analysis.dto import PatternResult
from myapp.app.training_engine.training_analysis.constants import (
    PATTERN_LOW_THRESHOLD,
    PATTERN_HIGH_THRESHOLD,
)
from myapp.app.training_engine.training_analysis.analyzers.utils import movement_pattern
from myapp.app.services.training.load_index_service import _compute_exercise_load


def analyse_patterns(
    sessions: List,
    target_day: date,
    exercise_map: Mapping[object, object],
    user_weight: float,
    days: int = 14,
) -> PatternResult:
    start = target_day - timedelta(days=days)
    window = [
        s
        for s in sessions
        if s.started_at and start <= s.started_at.date() <= target_day
    ]

    pattern_loads: Dict[str, float] = {}

    for s in window:
        internal = float(getattr(s, "internal_load", 1.0) or 1.0)
        total_session_load = 0.0
        per_exercise: Dict[object, float] = {}

        for se in s.exercises or []:
            ex = exercise_map.get(se.exercise_id)
            if not ex:
                continue

            sets = se.sets_done or se.sets_planned or 0
            reps = se.reps_done or se.reps_planned or "0"
            load = se.load_done or se.load_planned or 0

            ex_load = _compute_exercise_load(ex, sets, reps, load, user_weight)
            per_exercise[se.exercise_id] = ex_load
            total_session_load += ex_load

        if total_session_load <= 0:
            continue

        for ex_id, ex_load in per_exercise.items():
            ex = exercise_map.get(ex_id)
            if not ex:
                continue

            share = ex_load / total_session_load
            mp = movement_pattern(ex)
            pattern_loads[mp] = pattern_loads.get(mp, 0.0) + share * internal

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

    for p, v in pattern_loads.items():
        r = v / total if total > 0 else 0.0
        if r < PATTERN_LOW_THRESHOLD:
            weak_patterns.append(p)
        elif r > PATTERN_HIGH_THRESHOLD:
            overloaded_patterns.append(p)

    return {
        "weak_patterns": weak_patterns,
        "overloaded_patterns": overloaded_patterns,
        "pattern_loads": pattern_loads,
        "message": "movement patterns analysed",
    }
