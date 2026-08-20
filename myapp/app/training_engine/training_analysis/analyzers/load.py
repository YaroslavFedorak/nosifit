from typing import List
from datetime import date, timedelta

from myapp.app.training_engine.training_analysis.dto import LoadResult


def analyse_load(
    sessions: List,
    target_day: date,
    days: int = 7,
) -> LoadResult:
    start = target_day - timedelta(days=days)

    window = [
        session
        for session in sessions
        if session.started_at and start <= session.started_at.date() <= target_day
    ]

    if not window:
        return {
            "status": "unknown",
            "avg_rpe": 0.0,
            "sessions_count": 0,
            "message": "no load data",
        }

    rpes = []

    for session in window:
        rpe = getattr(session, "rpe_avg", None)

        if rpe is not None:
            rpes.append(float(rpe))

    avg_rpe = sum(rpes) / len(rpes) if rpes else 0.0

    if avg_rpe >= 8:
        status = "very_hard"
    elif avg_rpe >= 6:
        status = "hard"
    elif avg_rpe >= 4:
        status = "moderate"
    else:
        status = "easy"

    return {
        "status": status,
        "avg_rpe": round(avg_rpe, 2),
        "sessions_count": len(window),
        "message": "training load analysed",
    }
