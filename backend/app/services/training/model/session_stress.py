"""Session-level metrics for the dashboard and heatmap.

This is a separate tree from the muscle model: it describes how much hard
work a session or day contained and never blocks or prioritises muscles.

* hard_sets                       - sets weighted by proximity to failure
* session_training_stress_proxy   - sets weighted by fatigue cost; a proxy,
                                    not a measured systemic fatigue
* volume_load_kg                  - tonnage, descriptive only
* muscle_sets                     - effective sets per muscle
"""

from collections import defaultdict
from datetime import date, timedelta
from statistics import median
from typing import Callable, Dict, Iterable, Mapping, Sequence

from . import parameters as P
from .stimulus import Dose


def summarize(doses: Iterable[Dose]) -> Dict:
    hard = 0.0
    stress = 0.0
    tonnage = 0.0
    heavy = 0
    muscles: Dict[str, float] = defaultdict(float)
    for dose in doses:
        hard += dose.stimulus_sets
        stress += dose.fatigue_sets
        tonnage += dose.volume_load_kg
        heavy += dose.heavy_sets
        for muscle, sets in dose.muscle_stimulus:
            muscles[muscle] += sets
    return {
        "hard_sets": round(hard, 1),
        "session_training_stress_proxy": round(stress, 1),
        "volume_load_kg": round(tonnage, 1),
        "heavy_sets": heavy,
        "muscle_sets": {m: round(v, 2) for m, v in sorted(muscles.items()) if v > 0},
    }


def daily_stress(doses: Iterable[Dose], day_of: Callable) -> Dict[date, float]:
    per_day: Dict[date, float] = defaultdict(float)
    for dose in doses:
        per_day[day_of(dose.performed_at)] += dose.fatigue_sets
    return dict(per_day)


def typical_session_stress(per_day: Mapping[date, float], day: date) -> float:
    """Median stress proxy of training days before ``day`` (with a floor)."""
    start = day - timedelta(days=P.STRESS_BASELINE_DAYS)
    values = [v for d, v in per_day.items() if start <= d < day and v > 0]
    baseline = median(values) if values else 0.0
    return max(baseline, P.STRESS_MIN_TYPICAL_SETS)


def stress_level(value: float, typical: float) -> int:
    if value <= 0:
        return 0
    ratio = value / typical
    return 1 + sum(1 for bound in P.STRESS_LEVEL_RATIOS if ratio >= bound)


def day_levels(per_day: Mapping[date, float], days: Sequence[date]) -> Dict[date, Dict]:
    result = {}
    for day in days:
        value = per_day.get(day, 0.0)
        typical = typical_session_stress(per_day, day)
        result[day] = {
            "session_training_stress_proxy": round(value, 1),
            "typical": round(typical, 1),
            "level": stress_level(value, typical),
        }
    return result
