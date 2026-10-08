"""Plain, immutable inputs of the training model.

The model never touches ORM objects directly: the repository converts rows
into these records so every calculation is a pure function of them.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, FrozenSet, Mapping, Optional, Tuple


@dataclass(frozen=True)
class ExerciseInfo:
    id: str
    slug: str
    name: str
    movement_pattern: str
    measurement_type: str
    load_type: Optional[str]
    equipment: Tuple[str, ...]
    difficulty: int
    risk_level: int
    # Catalog muscle_load_profile: share of the exercise per muscle (sums to 1).
    profile: Tuple[Tuple[str, float], ...]
    primary: FrozenSet[str]
    secondary: FrozenSet[str]
    bodyweight_ratio: Optional[float] = None
    prescription: Mapping[str, Any] = field(default_factory=dict, compare=False, hash=False)

    @staticmethod
    def from_mapping(data: Mapping[str, Any]) -> "ExerciseInfo":
        profile = data.get("muscle_load_profile") or {}
        return ExerciseInfo(
            id=str(data.get("id") or data.get("slug")),
            slug=str(data.get("slug") or data.get("id") or ""),
            name=str(data.get("name") or data.get("slug") or ""),
            movement_pattern=_norm(data.get("movement_pattern")),
            measurement_type=str(data.get("measurement_type") or "reps"),
            load_type=data.get("load_type"),
            equipment=tuple(_norm(item) for item in (data.get("equipment") or [])),
            difficulty=int(data.get("difficulty") or 1),
            risk_level=int(data.get("risk_level") or 1),
            profile=tuple(
                sorted(
                    (_norm(muscle), float(share))
                    for muscle, share in profile.items()
                    if share and float(share) > 0
                )
            ),
            primary=frozenset(_norm(m) for m in (data.get("muscles_primary") or [])),
            secondary=frozenset(_norm(m) for m in (data.get("muscles_secondary") or [])),
            bodyweight_ratio=(
                float(data["bodyweight_ratio"]) if data.get("bodyweight_ratio") else None
            ),
            prescription=dict(data.get("prescription") or {}),
        )


@dataclass(frozen=True)
class LoggedEntry:
    """One exercise as performed in a session (sets x reps or sets x seconds)."""

    session_id: Optional[int]
    exercise_id: str
    performed_at: datetime
    sets: int
    reps: Optional[int] = None
    duration_sec: Optional[int] = None
    load_kg: float = 0.0
    rpe: Optional[float] = None


@dataclass(frozen=True)
class SleepNight:
    """Total sleep that ended on ``night`` (the morning date)."""

    night: date
    minutes: int


def _norm(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", "-").replace(" ", "-")
