from typing import Dict, List, Mapping
from datetime import date, timedelta
from myapp.app.training_engine.training_analysis.dto import (
    ProgressionResult,
    ProgressionDetails,
)
from myapp.app.training_engine.training_analysis.constants import (
    PROGRESSION_MIN_WEEKS,
    PROGRESSION_GOOD_THRESHOLD,
    PROGRESSION_REGRESSION_THRESHOLD,
    PROGRESSION_PLATEAU_THRESHOLD,
)
from myapp.app.services.training.load_index_service import _compute_exercise_load


def analyse_progression(
    sessions: List,
    target_day: date,
    exercise_map: Mapping[object, object],
    user_weight: float,
    weeks: int = 6,
) -> ProgressionResult:
    start = target_day - timedelta(days=weeks * 7)
    window = [
        s
        for s in sessions
        if s.started_at and start <= s.started_at.date() <= target_day
    ]

    if not window:
        return {"status": "unknown", "details": {}, "message": "no progression data"}

    weekly: Dict[object, Dict[int, float]] = {}

    for s in window:
        week = (target_day - s.started_at.date()).days // 7

        for se in s.exercises or []:
            ex = exercise_map.get(se.exercise_id)
            if not ex:
                continue

            sets = se.sets_done or se.sets_planned or 0
            reps = se.reps_done or se.reps_planned or "0"
            load = se.load_done or se.load_planned or 0

            ex_load = _compute_exercise_load(ex, sets, reps, load, user_weight)

            weekly.setdefault(se.exercise_id, {})
            weekly[se.exercise_id][week] = (
                weekly[se.exercise_id].get(week, 0.0) + ex_load
            )

    details: Dict[str, ProgressionDetails] = {}
    progress = plateau = regression = 0

    for ex_id, weeks_data in weekly.items():
        if len(weeks_data) < PROGRESSION_MIN_WEEKS:
            continue

        sorted_w = sorted(weeks_data.items())

        baseline_avg = sum(v for _, v in sorted_w[-2:]) / 2
        current_avg = sum(v for _, v in sorted_w[:2]) / 2

        if baseline_avg <= 0:
            continue

        change = (current_avg - baseline_avg) / baseline_avg

        details[str(ex_id)] = {
            "baseline_avg": baseline_avg,
            "current_avg": current_avg,
            "change": change,
        }

        if change > PROGRESSION_GOOD_THRESHOLD:
            progress += 1
        elif change < PROGRESSION_REGRESSION_THRESHOLD:
            regression += 1
        elif abs(change) < PROGRESSION_PLATEAU_THRESHOLD:
            plateau += 1

    status = "mixed"
    if regression > 0:
        status = "regression"
    elif progress > 0 and plateau == 0:
        status = "progress"
    elif plateau > 0 and progress == 0:
        status = "plateau"

    return {"status": status, "details": details, "message": "progress analysed"}
