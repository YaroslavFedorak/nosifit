"""Rules for one day of a weekly training plan: location, equipment, fit.

Training location (where) and equipment (what is at hand) are separate
facts. A plan day stores both:

* ``location``  - ``home``, ``gym`` or ``outdoors``;
* ``equipment`` - the equipment slugs available that day, or ``None`` when
  the day is not restricted (a gym, or a hand-built day nobody constrained).

``bodyweight`` is always available and never needs to be listed.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, FrozenSet, Iterable, Optional, Sequence

from backend.app.utils.validation import ValidationError

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
LOCATIONS = ("home", "gym", "outdoors")
BODYWEIGHT = "bodyweight"

# Equipment that can be used in a park or on a street: fixed outdoor
# stations (pull-up bar, dip bars, rings on a bar) and what fits in a bag.
OUTDOOR_EQUIPMENT = frozenset({BODYWEIGHT, "bar", "dip-bars", "rings", "band", "jump-rope"})

_EQUIPMENT_FILE = Path(__file__).resolve().parents[2] / "training" / "data" / "equipment" / "equipment.json"


@lru_cache(maxsize=1)
def known_equipment() -> FrozenSet[str]:
    with open(_EQUIPMENT_FILE, "r", encoding="utf-8") as handle:
        return frozenset(item["slug"] for item in json.load(handle))


def clean_location(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    if not isinstance(value, str) or value.strip().lower() not in LOCATIONS:
        raise ValidationError("location must be home, gym or outdoors")
    return value.strip().lower()


def clean_equipment(value: Any) -> Optional[list]:
    """Sorted unique known slugs; ``None`` stays ``None`` (no restriction)."""
    if value is None:
        return None
    if not isinstance(value, list) or len(value) > len(known_equipment()):
        raise ValidationError("equipment must be a list of equipment slugs")
    slugs = set()
    for item in value:
        slug = item.strip().lower() if isinstance(item, str) else None
        if slug not in known_equipment():
            raise ValidationError("unknown equipment")
        slugs.add(slug)
    return sorted(slugs - {BODYWEIGHT})


def available_equipment(
    location: Optional[str],
    equipment: Optional[Sequence[str]],
    owned: Iterable[str] = (),
) -> Optional[FrozenSet[str]]:
    """Equipment a day can use; ``None`` means no restriction.

    Explicit day equipment wins, otherwise a gym is unrestricted and home or
    outdoors fall back to the equipment the user owns. Outdoors never exceeds
    what can be used outside, whatever was selected.
    """
    if equipment is not None:
        usable = frozenset(equipment) | {BODYWEIGHT}
    elif location == "gym":
        return None
    elif location in ("home", "outdoors"):
        usable = frozenset(owned) | {BODYWEIGHT}
    else:
        return None
    if location == "outdoors":
        usable &= OUTDOOR_EQUIPMENT
    return usable


def missing_equipment(required: Iterable[str], available: Optional[FrozenSet[str]]) -> list:
    """Equipment the exercise needs that the day does not have."""
    if available is None:
        return []
    return sorted(set(required) - {BODYWEIGHT} - set(available))
