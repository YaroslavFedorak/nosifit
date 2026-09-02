from dataclasses import dataclass


@dataclass
class MobilityIndex:

    # Mobility score based on: hip mobility, shoulder mobility, thoracic mobility, ankle mobility

    hip: int  # 1–5
    shoulder: int
    thoracic: int
    ankle: int

    def score(self) -> float:
        raw = (self.hip + self.shoulder + self.thoracic + self.ankle) / 20
        return round(raw * 100, 2)
