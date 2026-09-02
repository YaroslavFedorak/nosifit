from typing import Dict, Any


class PlanValidator:
    @staticmethod
    def validate(days: Dict[str, Any]) -> bool:
        if not isinstance(days, dict) or not days:
            raise ValueError("Plan must contain at least one day")
        for key, day in days.items():
            if hasattr(day, "exercises"):
                exercises = day.exercises
            elif isinstance(day, dict):
                exercises = day.get("exercises", [])
            else:
                raise ValueError(f"Day {key} has invalid type")
            if not isinstance(exercises, list) or not exercises:
                raise ValueError(f"Day {key} has no exercises")
        return True
