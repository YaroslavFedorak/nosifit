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
from typing import Callable, Dict, Iterable, List, Mapping, Sequence

from . import parameters as P
from .numeric import round_half_up
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


def _baseline_days(per_day: Mapping[date, float], day: date) -> List[float]:
    start = day - timedelta(days=P.STRESS_BASELINE_DAYS)
    return [v for d, v in per_day.items() if start <= d < day and v > 0]


def typical_session_stress(per_day: Mapping[date, float], day: date) -> float:
    """Median stress proxy of training days before ``day`` (with a floor)."""
    values = _baseline_days(per_day, day)
    baseline = median(values) if values else 0.0
    return max(baseline, P.STRESS_MIN_TYPICAL_SETS)


def heatmap_typical_stress(per_day: Mapping[date, float], day: date) -> float:
    """Typical session for the heatmap: the user's median shrunk toward a prior.

    (k * median + w * prior) / (k + w), k = training days in the baseline
    window. Without history it is the prior; with history it converges to the
    user's own median smoothly instead of switching at a threshold.
    """
    values = _baseline_days(per_day, day)
    weight = P.HEATMAP_PRIOR_SESSIONS
    prior = P.HEATMAP_PRIOR_TYPICAL_STRESS
    if not values:
        return prior
    return (len(values) * median(values) + weight * prior) / (len(values) + weight)


def intensity_percent(value: float, typical: float) -> int:
    """Relative intensity of a day for the heatmap, 0-100.

    Linear in the ratio to the typical session and capped at
    HEATMAP_FULL_SCALE_RATIO; any training day shows at least 1%.
    """
    if value <= 0:
        return 0
    ratio = value / typical
    percent = round_half_up(100 * min(1.0, ratio / P.HEATMAP_FULL_SCALE_RATIO))
    return max(percent, 1)


def day_levels(per_day: Mapping[date, float], days: Sequence[date]) -> Dict[date, Dict]:
    result = {}
    for day in days:
        value = per_day.get(day, 0.0)
        heatmap_typical = heatmap_typical_stress(per_day, day)
        result[day] = {
            "session_training_stress_proxy": round(value, 1),
            # Recovery notes compare against this baseline (unchanged floor).
            "typical": round(typical_session_stress(per_day, day), 1),
            "intensity_percent": intensity_percent(value, heatmap_typical),
        }
    return result
