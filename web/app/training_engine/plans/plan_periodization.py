from typing import Dict


class PlanPeriodization:
    @staticmethod
    def apply_linear(week: int) -> Dict:
        return {"intensity": 0.6 + week * 0.05, "volume": 1.0}

    @staticmethod
    def apply_wave(week: int) -> Dict:
        wave = [0.6, 0.75, 0.65, 0.8]
        return {"intensity": wave[(week - 1) % len(wave)], "volume": 1.0}

    @staticmethod
    def apply_block(week: int) -> Dict:
        if week <= 3:
            return {"intensity": 0.6, "volume": 1.2}
        if week == 4:
            return {"intensity": 0.5, "volume": 0.8}
        return {"intensity": 0.7, "volume": 1.0}

    @staticmethod
    def apply(model: str, week: int) -> Dict:
        if model == "wave":
            return PlanPeriodization.apply_wave(week)
        if model == "block":
            return PlanPeriodization.apply_block(week)
        return PlanPeriodization.apply_linear(week)
