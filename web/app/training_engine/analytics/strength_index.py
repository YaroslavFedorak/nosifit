from dataclasses import dataclass
from typing import Dict


@dataclass
class StrengthIndex:

    # Calculates a composite strength index based on: push strength (pushups), leg strength (squats), core strength (situps), optional: grip strength, plank time

    pushups: int
    squats: int
    situps: int
    weight: float

    def normalized_push(self) -> float:
        return min(self.pushups / 50, 1.0)

    def normalized_squat(self) -> float:
        return min(self.squats / 60, 1.0)

    def normalized_core(self) -> float:
        return min(self.situps / 60, 1.0)

    def relative_strength(self) -> float:

        # Rough estimate - more reps at lower bodyweight = higher score

        total_reps = self.pushups + self.squats + self.situps
        return min((total_reps / self.weight) / 3, 1.0)

    def score(self) -> float:

        # Weighted composite score.

        return round((
            self.normalized_push() * 0.35 +
            self.normalized_squat() * 0.35 +
            self.normalized_core() * 0.20 +
            self.relative_strength() * 0.10
        ) * 100, 2)

    def breakdown(self) -> Dict:
        return {
            "push_strength": self.normalized_push(),
            "leg_strength": self.normalized_squat(),
            "core_strength": self.normalized_core(),
            "relative_strength": self.relative_strength(),
            "total_score": self.score()
        }
