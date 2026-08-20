from typing import Mapping, Dict, List
from datetime import date, timedelta

from myapp.app.training_engine.models.exercise import Exercise
from myapp.app.training_engine.training_analysis.dto import FrequencyResult
from myapp.app.training_engine.training_analysis.analyzers.utils import (
    primary_muscles,
)


def analyse_frequency(
    sessions: List,
    target_day: date,
    exercise_map: Mapping[object, Exercise],
    days: int = 28,
) -> FrequencyResult:
    start = target_day - timedelta(days=days)

    window = [
        session
        for session in sessions
        if session.started_at and start <= session.started_at.date() <= target_day
    ]

    counts: Dict[str, int] = {}

    for session in window:
        session_muscles = set()

        for session_exercise in session.exercises or []:
            exercise = exercise_map.get(session_exercise.exercise_id)

            if not exercise:
                continue

            for muscle in primary_muscles(exercise):
                session_muscles.add(muscle)

        for muscle in session_muscles:
            counts[muscle] = counts.get(muscle, 0) + 1

    return {
        "counts": counts,
        "message": "muscle frequency analysed",
    }
