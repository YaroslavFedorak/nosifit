from typing import Dict, List
from datetime import date, timedelta

from myapp.app.training_engine.training_analysis.dto import MuscleResult


def analyse_muscles(
    sessions: List,
    target_day: date,
    days: int = 14,
) -> MuscleResult:
    start = target_day - timedelta(days=days)

    window = [
        s
        for s in sessions
        if s.started_at and start <= s.started_at.date() <= target_day
    ]

    totals: Dict[str, float] = {}

    for session in window:
        for muscle, value in (session.muscle_loads or {}).items():
            muscle_key = str(muscle).lower()
            totals[muscle_key] = totals.get(muscle_key, 0.0) + float(value or 0.0)

    if not totals:
        return {
            "weak": [],
            "overloaded": [],
            "balanced": [],
            "totals": {},
            "balance_ratio": {},
            "message": "no muscle data",
        }

    values = sorted(totals.values())

    middle = len(values) // 2

    if len(values) % 2:
        median = values[middle]
    else:
        median = (values[middle - 1] + values[middle]) / 2

    weak: List[str] = []
    overloaded: List[str] = []
    balanced: List[str] = []
    ratios: Dict[str, float] = {}

    for muscle, value in totals.items():
        ratio = value / median if median > 0 else 1.0
        ratios[muscle] = round(ratio, 3)

        if ratio < 0.70:
            weak.append(muscle)
        elif ratio > 1.35:
            overloaded.append(muscle)
        else:
            balanced.append(muscle)

    weak.sort(key=lambda m: ratios[m])
    overloaded.sort(key=lambda m: ratios[m], reverse=True)
    balanced.sort(key=lambda m: abs(ratios[m] - 1.0))

    return {
        "weak": weak,
        "overloaded": overloaded,
        "balanced": balanced,
        "totals": totals,
        "balance_ratio": ratios,
        "message": "muscle balance analysed",
    }
