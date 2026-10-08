"""Weekly sets per major muscle for the training page widget.

Descriptive only: it adds up what sessions already stored in
``TrainingSession.muscle_loads`` (effective sets per muscle, written when a
session is saved) and sets it against the weekly target the model itself
uses. Nothing here feeds back into recommendations.

* period  - the current calendar week, Monday up to and including today.
* sets    - sum of the stored per-session muscle sets in that period.
* target  - the middle of the goal/experience band (WEEKLY_SET_TARGETS), the
            same point Stage 1 measures ``need`` against. Onboarding focus
            changes muscle priority in the model, not this target.
"""

from collections import defaultdict
from datetime import date, timedelta
from numbers import Real
from typing import Dict, Iterable, Mapping

from . import parameters as P
from .context import TrainingContext
from .status import weekly_targets


def week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def weekly_target_sets(context: TrainingContext) -> float:
    lower, upper = weekly_targets(context)
    return (lower + upper) / 2.0


def weekly_muscle_sets(muscle_loads: Iterable, context: TrainingContext) -> Dict:
    """Totals per major muscle from stored ``muscle_loads`` of one week.

    Rows written before model v2 hold exercise ids instead of muscle slugs;
    only major-muscle keys with numeric values are counted, so they add
    nothing."""
    totals: Dict[str, float] = defaultdict(float)
    for loads in muscle_loads:
        if not isinstance(loads, Mapping):
            continue
        for muscle, sets in loads.items():
            if muscle in P.MAJOR_MUSCLES and isinstance(sets, Real) and not isinstance(sets, bool) and sets > 0:
                totals[muscle] += float(sets)

    target = weekly_target_sets(context)
    return {
        "muscles": [
            {"muscle": muscle, "sets": round(totals[muscle], 1), "target_sets": target}
            for muscle in P.MAJOR_MUSCLES
        ],
    }
