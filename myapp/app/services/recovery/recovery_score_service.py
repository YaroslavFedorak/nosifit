from typing import Tuple

from myapp.app.services.recovery.sleep_service import SleepService
from myapp.app.services.recovery.habit_service import HabitService
from myapp.app.services.training_load_service import TrainingLoadService
from myapp.app.services.recovery.constants import (
    SLEEP_WEIGHT,
    TRAINING_WEIGHT,
    HABIT_WEIGHT,
    SLEEP_DEBT_DIVISOR,
    HEAVY_LOAD_RECOVERY_PENALTY,
    VERY_HEAVY_LOAD_RECOVERY_PENALTY,
    TRAINING_LOAD_HEAVY,
    TRAINING_LOAD_VERY_HEAVY,
)


class RecoveryScoreService:
    def __init__(self):
        self.sleep_service = SleepService()
        self.habit_service = HabitService()
        self.training_load = TrainingLoadService()

    def calculate_sleep_score(self, user_id: int) -> int:
        entry = self.sleep_service.get_last_sleep(user_id)
        if not entry:
            return 0
        return self.sleep_service.calculate_sleep_score(entry.duration_minutes)

    def calculate_habit_score(self, user_id: int) -> int:
        logs = self.habit_service.get_today_logs(user_id)
        if not logs:
            return 0
        completed = sum(1 for log in logs if log.completed)
        return int((completed / len(logs)) * 100)

    def calculate_training_score(self, user_id: int) -> int:
        load = self.training_load.get_daily_load(user_id)
        if load <= 40:
            return 30
        if load <= 80:
            return 60
        if load <= 120:
            return 80
        if load <= 160:
            return 90
        if load <= 180:
            return 70
        return 50

    def calculate_energy_score(self, sleep_score: int, habit_score: int) -> int:
        from myapp.app.services.recovery.constants import (
            ENERGY_SLEEP_WEIGHT,
            ENERGY_HABIT_WEIGHT,
        )

        return int(
            sleep_score * ENERGY_SLEEP_WEIGHT + habit_score * ENERGY_HABIT_WEIGHT
        )

    def _compute_penalties(
        self, user_id: int, required_minutes: int
    ) -> Tuple[int, int]:
        load = self.training_load.get_daily_load(user_id)
        debt_minutes = self.sleep_service.calculate_sleep_debt_minutes(
            user_id, required_minutes
        )

        load_penalty = 0
        if load > TRAINING_LOAD_HEAVY:
            load_penalty += HEAVY_LOAD_RECOVERY_PENALTY
        if load > TRAINING_LOAD_VERY_HEAVY:
            load_penalty += VERY_HEAVY_LOAD_RECOVERY_PENALTY

        debt_penalty = debt_minutes // SLEEP_DEBT_DIVISOR
        return load_penalty, debt_penalty

    def calculate_recovery_score(
        self,
        user_id: int,
        required_sleep_minutes: int,
        sleep_score: int,
        habit_score: int,
        training_score: int,
    ) -> int:
        load_penalty, debt_penalty = self._compute_penalties(
            user_id, required_sleep_minutes
        )

        base = int(
            sleep_score * SLEEP_WEIGHT
            + training_score * TRAINING_WEIGHT
            + habit_score * HABIT_WEIGHT
        )

        final = base - (load_penalty + debt_penalty)
        return max(0, min(100, final))
