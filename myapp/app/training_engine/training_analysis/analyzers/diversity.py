from typing import List, Mapping
from datetime import date, timedelta

from myapp.app.training_engine.models.exercise import Exercise
from myapp.app.training_engine.training_analysis.dto import DiversityResult
from myapp.app.training_engine.training_analysis.constants import (
    LOW_DIVERSITY_THRESHOLD,
    MEDIUM_DIVERSITY_THRESHOLD,
)


def analyse_diversity(
    sessions: List,
    target_day: date,
    exercise_map: Mapping[object, Exercise],
    days: int = 28,
) -> DiversityResult:
    start = target_day - timedelta(days=days)

    window = [
        session
        for session in sessions
        if session.started_at and start <= session.started_at.date() <= target_day
    ]

    names: List[str] = []

    for session in window:
        for session_exercise in session.exercises or []:
            exercise = exercise_map.get(session_exercise.exercise_id)

            if exercise:
                names.append(exercise.name)

    total = len(names)
    unique = len(set(names))

    if total == 0:
        return {
            "status": "unknown",
            "score": 0.0,
            "unique_exercises": 0,
            "total_exercises": 0,
            "message": "no exercise data",
        }

    score = unique / total

    if score >= MEDIUM_DIVERSITY_THRESHOLD:
        status = "high"
    elif score >= LOW_DIVERSITY_THRESHOLD:
        status = "medium"
    else:
        status = "low"

    return {
        "status": status,
        "score": round(score, 3),
        "unique_exercises": unique,
        "total_exercises": total,
        "message": "exercise diversity analysed",
    }
