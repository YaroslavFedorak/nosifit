from dataclasses import dataclass


@dataclass
class RecoveryIndex:
    
    # Recovery score based on: sleep hours, stress level, soreness, hydration

    sleep_hours: float
    stress: int  # 1–5
    soreness: int  # 1–5
    hydration_liters: float

    def score(self) -> float:
        sleep_score = min(self.sleep_hours / 8, 1.0)
        stress_score = 1 - (self.stress - 1) / 4
        soreness_score = 1 - (self.soreness - 1) / 4
        hydration_score = min(self.hydration_liters / 2.5, 1.0)

        return round((
            sleep_score * 0.4 +
            stress_score * 0.2 +
            soreness_score * 0.2 +
            hydration_score * 0.2
        ) * 100, 2)
