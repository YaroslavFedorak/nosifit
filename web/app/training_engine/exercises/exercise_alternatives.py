from typing import List
from ..models.exercise import Exercise
from .exercise_loader import ExerciseLoader
from .exercise_classifier import ExerciseClassifier


class ExerciseAlternatives:
    @staticmethod
    def by_muscle(exercise: Exercise) -> List[Exercise]:
        all_ex = ExerciseLoader.all()
        return ExerciseClassifier.by_primary_muscle(all_ex, exercise.muscles_primary[0]) if exercise.muscles_primary else []

    @staticmethod
    def by_pattern(exercise: Exercise) -> List[Exercise]:
        all_ex = ExerciseLoader.all()
        return ExerciseClassifier.by_movement_pattern(all_ex, exercise.movement_pattern)

    @staticmethod
    def by_equipment(exercise: Exercise, equipment: str) -> List[Exercise]:
        all_ex = ExerciseLoader.all()
        return ExerciseClassifier.by_equipment(all_ex, equipment)

    @staticmethod
    def similar_difficulty(exercise: Exercise, delta: int = 1) -> List[Exercise]:
        all_ex = ExerciseLoader.all()
        return ExerciseClassifier.by_difficulty(
            all_ex,
            exercise.difficulty - delta,
            exercise.difficulty + delta
        )
