from datetime import date, timedelta
from typing import Any, Dict, List, Mapping

from web.app.training_engine.training_analysis.constants import (
    PROGRESSION_GOOD_THRESHOLD,
    PROGRESSION_MIN_WEEKS,
    PROGRESSION_PLATEAU_THRESHOLD,
    PROGRESSION_REGRESSION_THRESHOLD,
)
from web.app.training_engine.training_analysis.dto import (
    ProgressionDetails,
    ProgressionResult,
)
from web.app.services.training.load.service import TrainingLoadService


def analyse_progression(
    sessions: List,
    target_day: date,
    exercise_map: Mapping[object, object],
    user: Any,
    weeks: int = 6,
) -> ProgressionResult:
    start = target_day - timedelta(days=weeks * 7)

    user_weight = float(getattr(user, "weight", 70) or 70)

    window = [
        session
        for session in sessions
        if session.started_at and start <= session.started_at.date() <= target_day
    ]

    if not window:
        return {
            "status": "unknown",
            "details": {},
            "message": "no progression data",
        }

    weekly: Dict[object, Dict[int, float]] = {}

    for session in window:
        week = (target_day - session.started_at.date()).days // 7

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

            weekly.setdefault(session_exercise.exercise_id, {})
            weekly[session_exercise.exercise_id][week] = (
                weekly[session_exercise.exercise_id].get(week, 0.0) + internal_load
            )

    details: Dict[str, ProgressionDetails] = {}

    progress = 0
    plateau = 0
    regression = 0

    for exercise_id, weeks_data in weekly.items():
        if len(weeks_data) < PROGRESSION_MIN_WEEKS:
            continue

        sorted_weeks = sorted(weeks_data.items())

        current_values = [value for _, value in sorted_weeks[:2]]
        baseline_values = [value for _, value in sorted_weeks[-2:]]

        current_avg = sum(current_values) / len(current_values)
        baseline_avg = sum(baseline_values) / len(baseline_values)

        if baseline_avg <= 0:
            continue

        change = (current_avg - baseline_avg) / baseline_avg

        details[str(exercise_id)] = {
            "baseline_avg": round(baseline_avg, 3),
            "current_avg": round(current_avg, 3),
            "change": round(change, 4),
        }

        if change > PROGRESSION_GOOD_THRESHOLD:
            progress += 1
        elif change < PROGRESSION_REGRESSION_THRESHOLD:
            regression += 1
        elif abs(change) < PROGRESSION_PLATEAU_THRESHOLD:
            plateau += 1

    if not details:
        status = "unknown"
    elif regression > progress and regression > plateau:
        status = "regression"
    elif progress > 0 and plateau == 0 and regression == 0:
        status = "progress"
    elif plateau > 0 and progress == 0 and regression == 0:
        status = "plateau"
    else:
        status = "mixed"

    return {
        "status": status,
        "details": details,
        "message": "progress analysed",
    }
