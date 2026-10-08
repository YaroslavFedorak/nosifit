"""Readiness: a bounded decision-support estimate, not a measured recovery.

    readiness_score = exp(-local_fatigue / READINESS_FATIGUE_SCALE) * sleep_modifier

Sleep only scales readiness (within [1 - SLEEP_MAX_READINESS_PENALTY, 1]); it
never changes stimulus, fatigue cost or exposure. User-facing levels are
Low readiness / Moderate readiness / Ready / Recovered with hysteresis.
"""

import math
from collections import defaultdict
from datetime import date, timedelta
from typing import Dict, Iterable, Optional, Sequence

from . import parameters as P
from .records import SleepNight

LEVEL_NAMES = tuple(name for name, _ in P.READINESS_LEVELS)
LEVEL_BOUNDS = tuple(bound for _, bound in P.READINESS_LEVELS)


def readiness_from_fatigue(fatigue: float) -> float:
    return math.exp(-max(fatigue, 0.0) / P.READINESS_FATIGUE_SCALE)


def sleep_debt_minutes(nights: Iterable[SleepNight], on: date) -> float:
    """Recency-weighted sleep deficit up to the night ending on ``on``.

    Nights without data contribute nothing: missing data is not bad sleep.
    """
    per_night: Dict[date, int] = defaultdict(int)
    for night in nights:
        per_night[night.night] += max(int(night.minutes or 0), 0)

    debt = 0.0
    for offset in range(P.SLEEP_LOOKBACK_NIGHTS):
        day = on - timedelta(days=offset)
        if day not in per_night:
            continue
        deficit = max(P.SLEEP_NEED_MINUTES - per_night[day], 0)
        debt += deficit * math.exp(-offset / P.SLEEP_DEBT_TAU_NIGHTS)
    return debt


def sleep_modifier(nights: Iterable[SleepNight], on: date) -> float:
    debt = sleep_debt_minutes(nights, on)
    penalty = 1.0 - math.exp(-debt / P.SLEEP_DEBT_SCALE_MINUTES)
    return 1.0 - P.SLEEP_MAX_READINESS_PENALTY * penalty


def hysteresis_index(
    value: float,
    bounds: Sequence[float],
    previous: Optional[int],
    margin: float,
) -> int:
    """Index of the highest bound <= value, changing from ``previous`` only when
    the value clears a bound by ``margin``. ``bounds`` must be ascending and
    start with the lowest possible value."""
    plain = max(i for i, bound in enumerate(bounds) if value >= bound or i == 0)
    if previous is None or plain == previous:
        return plain
    if plain > previous:
        up = [i for i in range(previous + 1, len(bounds)) if value >= bounds[i] + margin]
        return max(up) if up else previous
    if value >= bounds[previous] - margin:
        return previous
    down = [i for i in range(previous) if value >= bounds[i] - margin or i == 0]
    return max(down)


def readiness_level_index(score: float, previous: Optional[int] = None) -> int:
    return hysteresis_index(score, LEVEL_BOUNDS, previous, P.READINESS_HYSTERESIS)


def readiness_level(score: float, previous: Optional[int] = None) -> str:
    return LEVEL_NAMES[readiness_level_index(score, previous)]
