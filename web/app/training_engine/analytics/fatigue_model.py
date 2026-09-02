from dataclasses import dataclass


@dataclass
class FatigueModel:

    # Estimates fatigue level based on: sleep deficit, stress, soreness, training load

    sleep_hours: float
    stress: int
    soreness: int
    training_load: float  # arbitrary units

    def fatigue_score(self) -> float:
        sleep_penalty = max(0, 8 - self.sleep_hours) * 1.2
        stress_penalty = (self.stress - 1) * 1.5
        soreness_penalty = (self.soreness - 1) * 1.2
        load_penalty = self.training_load / 100

        return round(sleep_penalty + stress_penalty + soreness_penalty + load_penalty, 2)

    def is_overtrained(self) -> bool:
        return self.fatigue_score() > 10
