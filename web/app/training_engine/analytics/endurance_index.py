from dataclasses import dataclass


@dataclass
class EnduranceIndex:

    # Estimates muscular endurance based on: reps, time under tension, bodyweight

    pushups: int
    squats: int
    plank_sec: int
    weight: float

    def muscular_endurance(self) -> float:
        reps_score = (self.pushups + self.squats) / 120
        plank_score = self.plank_sec / 180
        return min((reps_score * 0.6 + plank_score * 0.4), 1.0)

    def relative_endurance(self) -> float:
        return min((self.pushups + self.squats) / self.weight / 2, 1.0)

    def score(self) -> float:
        return round((
            self.muscular_endurance() * 0.7 +
            self.relative_endurance() * 0.3
        ) * 100, 2)
