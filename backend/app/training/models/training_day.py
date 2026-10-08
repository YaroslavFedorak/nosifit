from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.app.training.exercises.prescription import build_entry


@dataclass
class TrainingDay:
    day_name: Optional[str] = None
    name: Optional[str] = None
    environment: Optional[List[str]] = None
    exercises: List[Dict[str, Any]] = field(default_factory=list)

    def add_exercise(
        self, exercise=None, sets=None, reps=None, duration_sec=None, load=0
    ):
        """Add an exercise; missing values come from its catalog prescription."""
        entry = build_entry(
            exercise,
            sets=sets,
            reps=reps,
            duration_sec=duration_sec,
            load=load,
        )
        entry["exercise"] = exercise
        self.exercises.append(entry)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            day_name=data.get("day_name") or data.get("name"),
            name=data.get("day_name") or data.get("name"),
            environment=data.get("environment"),
            exercises=list(data.get("exercises", [])),
        )

    def to_dict(self):
        return {
            "day_name": self.day_name or self.name,
            "name": self.day_name or self.name,
            "environment": self.environment,
            "exercises": [
                {
                    "exercise": (
                        ex["exercise"].to_dict()
                        if hasattr(ex["exercise"], "to_dict")
                        else ex["exercise"]
                    ),
                    "measurement_type": ex.get("measurement_type", "reps"),
                    "sets": ex["sets"],
                    "reps": ex.get("reps"),
                    "duration_sec": ex.get("duration_sec"),
                    "per_side": ex.get("per_side", False),
                    "load": ex.get("load", 0),
                }
                for ex in self.exercises
            ],
        }

