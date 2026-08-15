from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional

from myapp.app import db
from myapp.app.models.recovery.habit import RecoveryHabit
from myapp.app.models.recovery.user_habit import UserRecoveryHabit
from myapp.app.models.recovery.habit_log import RecoveryHabitLog
from myapp.app.models.training_session import TrainingSession
from myapp.app.services.recovery.constants import (
    MUSCLE_LOW_LOAD,
    MUSCLE_HIGH_LOAD,
    MUSCLE_TRAINING_GAP_DAYS,
    MUSCLE_TRAINING_RECOVERY_DAYS,
    MAX_RECOMMENDATIONS,
)


class RecommendationService:
    def __init__(self):
        pass

    def _build_context(
        self, user_id: int, window_days: int = 7, target_date: Optional[date] = None
    ):
        target_date = target_date if target_date is not None else date.today()
        start = target_date - timedelta(days=window_days - 1)

        sessions = (
            TrainingSession.query.filter(
                TrainingSession.user_id == user_id,
                TrainingSession.started_at
                >= datetime.combine(start, datetime.min.time()),
                TrainingSession.started_at
                <= datetime.combine(target_date, datetime.max.time()),
            )
            .order_by(TrainingSession.started_at.asc())
            .all()
        )

        muscle_stats = {}
        last_trained = {}

        for s in sessions:
            s_date = s.started_at.date() if s.started_at else None
            for m, load in (s.muscle_loads or {}).items():
                muscle_stats[m] = muscle_stats.get(m, 0) + (load or 0)
                if s_date:
                    last_trained[m] = max(last_trained.get(m, date.min), s_date)

        avg = {}
        for m, total in muscle_stats.items():
            avg[m] = total / window_days

        return {
            "sessions": sessions,
            "muscle_stats": muscle_stats,
            "muscle_avg": avg,
            "last_trained": last_trained,
            "target_date": target_date,
        }

    def _recovery_recommendations(
        self, recovery_score: Optional[int], energy_score: Optional[int]
    ) -> List[Dict[str, Any]]:
        recs = []
        if recovery_score is None:
            return recs

        if recovery_score < 40:
            recs.append(
                {
                    "type": "recovery",
                    "id": "full_recovery",
                    "priority": "high",
                    "text": "Focus on recovery today and avoid high-intensity training",
                    "reason": {"recovery_score": recovery_score},
                }
            )
        elif recovery_score < 60:
            recs.append(
                {
                    "type": "recovery",
                    "id": "light_training",
                    "priority": "medium",
                    "text": "Keep today's training light and focus on technique",
                    "reason": {"recovery_score": recovery_score},
                }
            )

        if energy_score is not None and energy_score < 40:
            recs.append(
                {
                    "type": "recovery",
                    "id": "low_energy",
                    "priority": "medium",
                    "text": "Energy is low — prefer light activity or active recovery",
                    "reason": {"energy_score": energy_score},
                }
            )

        return recs

    def _habit_recommendations(
        self, habit_score: Optional[int]
    ) -> List[Dict[str, Any]]:
        recs = []
        if habit_score is None:
            return recs
        if habit_score < 50:
            recs.append(
                {
                    "type": "habit",
                    "id": "complete_habits",
                    "priority": "medium",
                    "text": "Complete your recovery habits to improve recovery",
                    "reason": {"habit_score": habit_score},
                }
            )
        return recs

    def _muscle_recommendations(
        self,
        muscle_stats: Dict[str, float],
        muscle_avg: Dict[str, float],
        last_trained: Dict[str, date],
        recovery_score: Optional[int],
        target_date: date,
    ) -> List[Dict[str, Any]]:
        recs = []
        for m, recent in muscle_stats.items():
            avg = muscle_avg.get(m, 0) or 1.0
            rel = recent / avg if avg else 0.0
            last = last_trained.get(m)
            days_since = (target_date - last).days if last else 999
            recovery_hours = None
            if (
                recent >= MUSCLE_HIGH_LOAD
                and days_since <= MUSCLE_TRAINING_RECOVERY_DAYS
            ):
                recs.append(
                    {
                        "type": "muscle",
                        "id": f"rest_{m}",
                        "muscle": m,
                        "priority": "high",
                        "text": f"Give {m} more recovery after heavy recent load",
                        "reason": {
                            "recent_load": recent,
                            "days_since": days_since,
                            "relative": rel,
                        },
                    }
                )
                continue

            if (
                recent < MUSCLE_LOW_LOAD
                or rel < 0.6
                or days_since >= MUSCLE_TRAINING_GAP_DAYS
            ):
                if recovery_score is not None and recovery_score < 45:
                    continue
                recs.append(
                    {
                        "type": "exercise",
                        "id": f"train_{m}",
                        "muscle": m,
                        "priority": "medium",
                        "text": f"Consider training {m} (lower recent volume)",
                        "reason": {
                            "recent_load": recent,
                            "days_since": days_since,
                            "relative": rel,
                        },
                        "suggested_sets": 3,
                        "suggested_reps": "8-12",
                        "suggested_rpe": 7,
                    }
                )
        return recs

    def build_recommendations(
        self,
        user_id: int,
        sleep_score: Optional[int],
        recovery_score: Optional[int],
        energy_score: Optional[int],
        habit_score: Optional[int],
        daily_load: Optional[float],
        target_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        ctx = self._build_context(user_id, window_days=7, target_date=target_date)
        muscle_stats = ctx["muscle_stats"]
        muscle_avg = ctx["muscle_avg"]
        last_trained = ctx["last_trained"]
        td = ctx["target_date"]

        recs: List[Dict[str, Any]] = []
        recs.extend(self._recovery_recommendations(recovery_score, energy_score))
        recs.extend(self._habit_recommendations(habit_score))
        recs.extend(
            self._muscle_recommendations(
                muscle_stats, muscle_avg, last_trained, recovery_score, td
            )
        )

        recs_sorted = sorted(
            recs,
            key=lambda r: {"high": 0, "medium": 1, "low": 2}.get(
                r.get("priority", "low")
            ),
        )

        return recs_sorted[:MAX_RECOMMENDATIONS]
