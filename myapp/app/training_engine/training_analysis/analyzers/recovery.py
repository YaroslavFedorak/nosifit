from typing import List, Any
from datetime import date, timedelta

from myapp.app.training_engine.training_analysis.dto import RecoveryResult
from myapp.app.training_engine.training_analysis.constants import (
    RECOVERY_GOOD_SLEEP,
    RECOVERY_MEDIUM_SLEEP,
    RECOVERY_GOOD_FATIGUE,
    RECOVERY_MEDIUM_FATIGUE,
    RECOVERY_GOOD_STRESS,
    RECOVERY_MEDIUM_STRESS,
    RECOVERY_GOOD_SORENESS,
    RECOVERY_MEDIUM_SORENESS,
)


def analyse_recovery(
    user: Any,
    sessions: List,
    target_day: date,
    days: int = 7,
) -> RecoveryResult:
    start = target_day - timedelta(days=days)

    window = [
        session
        for session in sessions
        if session.started_at and start <= session.started_at.date() <= target_day
    ]

    sleep_values: List[float] = []
    fatigue_values: List[float] = []
    stress_values: List[float] = []
    soreness_values: List[float] = []

    fatigue_state = getattr(user, "fatigue_state", None)

    if fatigue_state:
        sleep = getattr(fatigue_state, "sleep", None)
        stress = getattr(fatigue_state, "stress", None)
        soreness = getattr(fatigue_state, "soreness", None)

        if sleep is not None:
            sleep_values.append(float(sleep))

        if stress is not None:
            stress_values.append(float(stress))

        if soreness is not None:
            soreness_values.append(float(soreness))

    for session in window:
        fatigue_before = getattr(session, "fatigue_before", None)
        fatigue_after = getattr(session, "fatigue_after", None)

        if fatigue_before is not None:
            fatigue_values.append(float(fatigue_before))

        if fatigue_after is not None:
            fatigue_values.append(float(fatigue_after))

    sleep_avg = sum(sleep_values) / len(sleep_values) if sleep_values else 7.0

    fatigue_avg = sum(fatigue_values) / len(fatigue_values) if fatigue_values else 0.0

    stress_avg = sum(stress_values) / len(stress_values) if stress_values else 0.0

    soreness_avg = (
        sum(soreness_values) / len(soreness_values) if soreness_values else 0.0
    )

    good = (
        sleep_avg >= RECOVERY_GOOD_SLEEP
        and fatigue_avg <= RECOVERY_GOOD_FATIGUE
        and stress_avg <= RECOVERY_GOOD_STRESS
        and soreness_avg <= RECOVERY_GOOD_SORENESS
    )

    medium = (
        sleep_avg >= RECOVERY_MEDIUM_SLEEP
        and fatigue_avg <= RECOVERY_MEDIUM_FATIGUE
        and stress_avg <= RECOVERY_MEDIUM_STRESS
        and soreness_avg <= RECOVERY_MEDIUM_SORENESS
    )

    if good:
        status = "good"
    elif medium:
        status = "medium"
    else:
        status = "low"

    return {
        "status": status,
        "sleep_hours_avg": round(sleep_avg, 2),
        "fatigue_avg": round(fatigue_avg, 2),
        "stress_avg": round(stress_avg, 2),
        "soreness_avg": round(soreness_avg, 2),
        "message": "recovery analysed",
    }
