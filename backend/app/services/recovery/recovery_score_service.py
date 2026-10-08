from typing import Tuple, Optional

from backend.app.services.recovery.sleep_service import SleepService
from backend.app.services.recovery.habit_service import HabitService
from backend.app.extensions import db
from backend.app.models.user import User
from backend.app.services.training.model import TrainingModelService
from backend.app.services.recovery.constants import (
    SLEEP_WEIGHT,
    TRAINING_WEIGHT,
    HABIT_WEIGHT,
    SLEEP_DEBT_DIVISOR,
)


class RecoveryScoreService:
    def __init__(self):
        self.sleep_service = SleepService()
        self.habit_service = HabitService()

    def calculate_sleep_score(self, duration_minutes: int) -> int:
        return self.sleep_service.calculate_sleep_score(duration_minutes)

    def calculate_habit_score(self, user_id: int, target_date=None) -> int:
        logs = self.habit_service.get_today_logs(user_id, target_date=target_date)
        habits = self.habit_service.get_user_habits(user_id)
        if not habits:
            return 0
        completed_ids = {log.user_habit_id for log in logs if log.completed}
        completed = sum(1 for h in habits if h.id in completed_ids)
        return int((completed / len(habits)) * 100)

    def calculate_training_score(self, user_id: int, target_date=None) -> int:
        """Readiness (0-100) of recently trained muscles from the training
        model; 100 when nothing was trained recently. Higher = more recovered."""
        user = db.session.get(User, user_id)
        if user is None:
            return 100
        return TrainingModelService.training_readiness_score(user, target_date)

    def calculate_energy_score(
        self, sleep_score: Optional[int], habit_score: int
    ) -> int:
        from backend.app.services.recovery.constants import (
            ENERGY_SLEEP_WEIGHT,
            ENERGY_HABIT_WEIGHT,
        )

        if sleep_score is None:
            sleep_score = 0
        return int(
            sleep_score * ENERGY_SLEEP_WEIGHT + habit_score * ENERGY_HABIT_WEIGHT
        )

    def _compute_penalties(
        self, user_id: int, required_minutes: int, target_date=None
    ) -> Tuple[int, int]:
        debt_minutes = self.sleep_service.calculate_sleep_debt_minutes(
            user_id, required_minutes
        )

        # Training fatigue is already part of the training score (readiness);
        # the former extra penalty on the raw legacy load is not applied.
        load_penalty = 0
        debt_penalty = debt_minutes // SLEEP_DEBT_DIVISOR
        return load_penalty, debt_penalty

    def calculate_recovery_score(
        self,
        user_id: int,
        required_sleep_minutes: int,
        sleep_score: int,
        habit_score: int,
        training_score: int,
        target_date=None,
    ) -> int:
        load_penalty, debt_penalty = self._compute_penalties(
            user_id, required_sleep_minutes, target_date=target_date
        )

        base = int(
            (sleep_score or 0) * SLEEP_WEIGHT
            + (training_score or 0) * TRAINING_WEIGHT
            + (habit_score or 0) * HABIT_WEIGHT
        )

        final = base - (load_penalty + debt_penalty)
        return max(0, min(100, final))

