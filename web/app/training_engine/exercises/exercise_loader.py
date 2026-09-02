import json
import os
from typing import Dict
from ..models.exercise import Exercise


class ExerciseLoader:
    _cache: Dict[str, Exercise] = {}

    @classmethod
    def load_base_exercises(cls, base_path: str):
        file_path = os.path.join(base_path, "base_exercises.json")
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        cls._cache = {}
        for ex_data in data:
            ex_id = ex_data.get("slug") or ex_data.get("id")
            if not ex_id:
                continue
            ex = Exercise(
                name=ex_data["name"],
                slug=ex_data["slug"],
                description=ex_data.get("description"),
                difficulty=ex_data.get("difficulty", 1),
                location=ex_data.get("location", "any"),
                movement_pattern=ex_data.get("movement_pattern"),
                risk_level=ex_data.get("risk_level", 1),
            )
            setattr(ex, "muscles_primary", ex_data.get("muscles_primary", []))
            setattr(ex, "muscles_secondary", ex_data.get("muscles_secondary", []))
            setattr(ex, "_legacy_equipment", ex_data.get("equipment", []))
            setattr(ex, "progression_chain", ex_data.get("progression_chain", []))
            setattr(ex, "regression_chain", ex_data.get("regression_chain", []))
            cls._cache[ex_id] = ex

    @classmethod
    def get(cls, exercise_id: str) -> Exercise:
        return cls._cache.get(exercise_id)

    @classmethod
    def all(cls) -> Dict[str, Exercise]:
        return cls._cache

    @classmethod
    def filter_by_environment(cls, env: str) -> Dict[str, Exercise]:
        return {k: v for k, v in cls._cache.items() if env in getattr(v, "environment", [])}
