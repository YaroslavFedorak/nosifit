"""Performance trend from estimated 1RM (strength-specific signal).

e1RM uses Epley with reps + RIR, only for loaded sets with few reps, where the
estimate is least unreliable. It describes progress; it does not feed the
stimulus or fatigue model.
"""

from datetime import datetime, timedelta
from typing import Dict, Iterable, Mapping, Optional

from . import parameters as P
from .records import ExerciseInfo, LoggedEntry
from .stimulus import effective_rir


def estimated_1rm(load_kg: float, reps: Optional[int], rpe: Optional[float]) -> Optional[float]:
    if not load_kg or load_kg <= 0 or not reps or reps <= 0:
        return None
    rir, _ = effective_rir(rpe)
    reps_to_failure = reps + rir
    if reps_to_failure > P.E1RM_MAX_REPS:
        return None
    return load_kg * (1.0 + reps_to_failure / 30.0)


def analyse_progression(
    entries: Iterable[LoggedEntry],
    exercises: Mapping[str, ExerciseInfo],
    now: datetime,
) -> Dict:
    weeks = P.PROGRESSION_WEEKS
    start = now - timedelta(weeks=weeks)
    half = weeks / 2.0
    early: Dict[str, float] = {}
    late: Dict[str, float] = {}

    for entry in entries:
        if not (start <= entry.performed_at <= now):
            continue
        value = estimated_1rm(entry.load_kg, entry.reps, entry.rpe)
        if value is None:
            continue
        weeks_ago = (now - entry.performed_at).days / 7.0
        bucket = late if weeks_ago < half else early
        bucket[entry.exercise_id] = max(bucket.get(entry.exercise_id, 0.0), value)

    details = {}
    counts = {"progress": 0, "plateau": 0, "regression": 0}
    for exercise_id in sorted(set(early) & set(late)):
        change = (late[exercise_id] - early[exercise_id]) / early[exercise_id]
        if change >= P.PROGRESSION_THRESHOLDS["progress"]:
            status = "progress"
        elif change <= P.PROGRESSION_THRESHOLDS["regression"]:
            status = "regression"
        else:
            status = "plateau"
        counts[status] += 1
        exercise = exercises.get(exercise_id)
        details[exercise.slug if exercise else exercise_id] = {
            "baseline_e1rm": round(early[exercise_id], 1),
            "current_e1rm": round(late[exercise_id], 1),
            "change": round(change, 4),
            "status": status,
        }

    if not details:
        overall = "unknown"
    elif counts["regression"] > counts["progress"] and counts["regression"] >= counts["plateau"]:
        overall = "regression"
    elif counts["progress"] and not counts["plateau"] and not counts["regression"]:
        overall = "progress"
    elif counts["plateau"] and not counts["progress"] and not counts["regression"]:
        overall = "plateau"
    else:
        overall = "mixed"

    return {"status": overall, "details": details, "message": "progress analysed"}
