from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TrainingDay:
    day_name: Optional[str] = None
    name: Optional[str] = None
    environment: Optional[List[str]] = None
    exercises: List[Dict[str, Any]] = field(default_factory=list)

    def add_exercise(self, exercise=None, sets=3, reps="8-12", load=0):
        entry = {
            "exercise": exercise,
            "sets": sets,
            "reps": reps,
            "load": load,
        }
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
                    "sets": ex["sets"],
                    "reps": ex["reps"],
                    "load": ex.get("load", 0),
                }
                for ex in self.exercises
            ],
        }
