from datetime import date
from typing import Dict, Any, Optional

from myapp.app import db
from myapp.app.models.recovery.daily_recovery_snapshot import DailyRecoverySnapshot
from myapp.app.services.recovery.recovery_score_service import RecoveryScoreService
from myapp.app.services.recovery.habit_service import HabitService


class SnapshotService:
    def __init__(self) -> None:
        self.scores = RecoveryScoreService()
        self.habits = HabitService()

    def update_snapshot(
        self,
        snapshot: DailyRecoverySnapshot,
        sleep_score: int,
        sleep_entry_data: Dict[str, Any],
        habit_score: int,
        training_score: int,
        energy_score: int,
        recovery_score: int,
    ) -> None:
        snapshot.sleep_score = sleep_score
        snapshot.sleep_duration_minutes = sleep_entry_data["duration"]
        snapshot.sleep_start = sleep_entry_data["start"]
        snapshot.sleep_end = sleep_entry_data["end"]
        snapshot.habit_score = habit_score
        snapshot.training_score = training_score
        snapshot.energy_score = energy_score
        snapshot.recovery_score = recovery_score

    def _get_sleep_for_date(self, user_id: int, target_date: date):
        if hasattr(self.scores.sleep_service, "get_sleep_for_date"):
            return self.scores.sleep_service.get_sleep_for_date(user_id, target_date)
        return self.scores.sleep_service.get_last_sleep(user_id)

    def generate_snapshot(
        self,
        user_id: int,
        target_date: Optional[date] = None,
        last_training_days: int = 0,
    ) -> DailyRecoverySnapshot:
        today = target_date or date.today()

        sleep_entry = self._get_sleep_for_date(user_id, today)

        if sleep_entry:
            sleep_data = {
                "sleep_score": self.scores.calculate_sleep_score(
                    sleep_entry.duration_minutes
                ),
                "duration": sleep_entry.duration_minutes,
                "start": sleep_entry.sleep_start,
                "end": sleep_entry.sleep_end,
            }
            habit_score = self.scores.calculate_habit_score(user_id, target_date=today)
            training_score = self.scores.calculate_training_score(
                user_id, target_date=today
            )
            energy_score = self.scores.calculate_energy_score(
                sleep_data["sleep_score"], habit_score
            )
            recovery_score = self.scores.calculate_recovery_score(
                user_id,
                required_sleep_minutes=8 * 60,
                sleep_score=sleep_data["sleep_score"],
                habit_score=habit_score,
                training_score=training_score,
                target_date=today,
            )
        else:
            sleep_data = {
                "sleep_score": None,
                "duration": None,
                "start": None,
                "end": None,
            }
            habit_score = self.scores.calculate_habit_score(user_id, target_date=today)
            training_score = self.scores.calculate_training_score(
                user_id, target_date=today
            )
            energy_score = None
            recovery_score = self.scores.calculate_recovery_score(
                user_id,
                required_sleep_minutes=8 * 60,
                sleep_score=0,
                habit_score=habit_score,
                training_score=training_score,
                target_date=today,
            )

        snapshot = DailyRecoverySnapshot.query.filter_by(
            user_id=user_id, date=today
        ).first()

        if snapshot:
            self.update_snapshot(
                snapshot,
                (
                    sleep_data["sleep_score"]
                    if sleep_data["sleep_score"] is not None
                    else 0
                ),
                sleep_data,
                habit_score,
                training_score,
                energy_score if energy_score is not None else 0,
                recovery_score,
            )
        else:
            snapshot = DailyRecoverySnapshot(
                user_id=user_id,
                date=today,
                sleep_score=(
                    sleep_data["sleep_score"]
                    if sleep_data["sleep_score"] is not None
                    else 0
                ),
                sleep_duration_minutes=sleep_data["duration"],
                sleep_start=sleep_data["start"],
                sleep_end=sleep_data["end"],
                habit_score=habit_score,
                training_score=training_score,
                energy_score=energy_score if energy_score is not None else 0,
                recovery_score=recovery_score,
            )
            db.session.add(snapshot)

        db.session.commit()
        return snapshot
