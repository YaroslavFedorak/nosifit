"""Training history: doses over time, historical exposure and local fatigue.

Exposure (from stimulus) and local fatigue (from fatigue cost) are two
separate quantities with separate time scales:

* exposure  E(t) = (7 / tau) * sum(stimulus_i * exp(-age_days_i / tau))
  reads as "effective sets per week"; one session of N sets right now
  gives E7 = N, and it fades smoothly instead of dropping out of a window.
* fatigue   L(t) = sum(fatigue_i * 2 ** (-age_hours_i / half_life))
"""

import math
from collections import defaultdict
from datetime import datetime
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

from . import parameters as P
from .records import ExerciseInfo, LoggedEntry
from .stimulus import Dose, entry_dose

SECONDS_PER_DAY = 86400.0
SECONDS_PER_HOUR = 3600.0


def build_doses(
    entries: Iterable[LoggedEntry],
    exercises: Mapping[str, ExerciseInfo],
    body_weight_kg: Optional[float] = None,
) -> List[Dose]:
    """Doses in chronological order; novelty uses the gap to the previous time
    the same exercise was performed."""
    ordered = sorted(
        entries,
        key=lambda e: (e.performed_at, e.session_id or 0, e.exercise_id),
    )
    last_seen: Dict[str, datetime] = {}
    doses: List[Dose] = []

    for entry in ordered:
        exercise = exercises.get(entry.exercise_id)
        if exercise is None or entry.sets <= 0:
            continue
        previous = last_seen.get(entry.exercise_id)
        days_since = (
            None
            if previous is None
            else (entry.performed_at - previous).total_seconds() / SECONDS_PER_DAY
        )
        doses.append(entry_dose(entry, exercise, days_since, body_weight_kg))
        if previous is None or entry.performed_at > previous:
            last_seen[entry.exercise_id] = entry.performed_at

    return doses


def _age_seconds(dose: Dose, now: datetime) -> Optional[float]:
    age = (now - dose.performed_at).total_seconds()
    return age if age >= 0 else None


def muscle_exposure(doses: Sequence[Dose], now: datetime, tau_days: float) -> Dict[str, float]:
    """Exponentially weighted stimulus per muscle, in effective sets per week."""
    totals: Dict[str, float] = defaultdict(float)
    for dose in doses:
        age = _age_seconds(dose, now)
        if age is None:
            continue
        weight = math.exp(-(age / SECONDS_PER_DAY) / tau_days)
        for muscle, sets in dose.muscle_stimulus:
            totals[muscle] += sets * weight
    scale = 7.0 / tau_days
    return {muscle: value * scale for muscle, value in totals.items()}


def muscle_fatigue(doses: Sequence[Dose], now: datetime) -> Dict[str, float]:
    """Residual local fatigue per muscle, in fatigue set-units."""
    totals: Dict[str, float] = defaultdict(float)
    for dose in doses:
        age = _age_seconds(dose, now)
        if age is None:
            continue
        weight = 2.0 ** (-(age / SECONDS_PER_HOUR) / P.FATIGUE_HALF_LIFE_HOURS)
        for muscle, fatigue in dose.muscle_fatigue:
            totals[muscle] += fatigue * weight
    return dict(totals)


def trend(recent: float, longer: float) -> str:
    """'up' / 'down' / 'stable' from E7 vs E28 with a dead band (descriptive)."""
    reference = max(longer, P.TREND_MIN_REFERENCE_SETS)
    change = (recent - longer) / reference
    if change > P.TREND_DEADBAND:
        return "up"
    if change < -P.TREND_DEADBAND:
        return "down"
    return "stable"


def last_trained(doses: Sequence[Dose], now: datetime) -> Dict[str, datetime]:
    """Last time each muscle got at least DIRECT_EXPOSURE_MIN_SETS from one dose."""
    result: Dict[str, datetime] = {}
    for dose in doses:
        if dose.performed_at > now:
            continue
        for muscle, sets in dose.muscle_stimulus:
            if sets >= P.DIRECT_EXPOSURE_MIN_SETS:
                current = result.get(muscle)
                if current is None or dose.performed_at > current:
                    result[muscle] = dose.performed_at
    return result


def last_done(doses: Sequence[Dose], now: datetime) -> Dict[str, datetime]:
    """Last time each exercise was performed."""
    result: Dict[str, datetime] = {}
    for dose in doses:
        if dose.performed_at <= now:
            current = result.get(dose.exercise_id)
            if current is None or dose.performed_at > current:
                result[dose.exercise_id] = dose.performed_at
    return result
