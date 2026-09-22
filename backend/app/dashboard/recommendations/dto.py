from dataclasses import asdict, dataclass
from typing import Any, Optional

PRIORITY_VALUES = {
    "high": 3,
    "medium": 2,
    "low": 1,
}


@dataclass(frozen=True)
class Recommendation:
    category: str
    id: str
    title: str
    description: str
    priority: str
    type: Optional[str] = None
    reason: Optional[str] = None
    suggested_sets: Optional[int] = None
    suggested_reps: Optional[int] = None
    suggested_rpe: Optional[float] = None
    score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("score", None)
        return data


@dataclass(frozen=True)
class DashboardRecommendations:
    daily: Optional[Recommendation]
    training: Optional[Recommendation]
    recovery: Optional[Recommendation]
    nutrition: Optional[Recommendation]

    def to_dict(self) -> dict[str, Any]:
        return {
            "daily": (self.daily.to_dict() if self.daily is not None else None),
            "categories": {
                "training": (
                    self.training.to_dict() if self.training is not None else None
                ),
                "recovery": (
                    self.recovery.to_dict() if self.recovery is not None else None
                ),
                "nutrition": (
                    self.nutrition.to_dict() if self.nutrition is not None else None
                ),
            },
        }

