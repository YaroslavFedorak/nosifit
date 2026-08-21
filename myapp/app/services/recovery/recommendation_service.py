from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from myapp.app.models.recovery.daily_recovery_snapshot import (
    DailyRecoverySnapshot,
)
from myapp.app.models.training_session import TrainingSession
from myapp.app.services.recovery.constants import (
    MAX_RECOMMENDATIONS,
    MUSCLE_HIGH_LOAD,
    MUSCLE_LOW_LOAD,
    MUSCLE_TRAINING_GAP_DAYS,
    MUSCLE_TRAINING_RECOVERY_DAYS,
)
from myapp.app.services.training.load_service import TrainingLoadService


class RecommendationService:
    @staticmethod
    def _get_recovery_data(
        user_id: int,
        target_date: date,
    ) -> Dict[str, Any]:
        snapshot = DailyRecoverySnapshot.query.filter_by(
            user_id=user_id,
            date=target_date,
        ).first()

        if snapshot is None:
            return {}

        return {
            "recovery_score": snapshot.recovery_score,
            "sleep_score": snapshot.sleep_score,
            "energy_score": snapshot.energy_score,
            "habit_score": snapshot.habit_score,
            "training_score": snapshot.training_score,
        }

    @staticmethod
    def _get_daily_load(
        user_id: int,
        target_date: date,
    ) -> Optional[float]:
        try:
            service = TrainingLoadService()
            load = service.get_daily_load(
                user_id,
                target_date=target_date,
            )

            return float(load) if load is not None else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _build_context(
        user_id: int,
        target_date: date,
        window_days: int = 7,
    ) -> Dict[str, Any]:
        start_date = target_date - timedelta(days=window_days - 1)
        end_date = target_date + timedelta(days=1)

        sessions = (
            TrainingSession.query.filter(
                TrainingSession.user_id == user_id,
                TrainingSession.started_at >= start_date,
                TrainingSession.started_at < end_date,
            )
            .order_by(TrainingSession.started_at.asc())
            .all()
        )

        muscle_total_load: Dict[str, float] = {}
        muscle_daily_load: Dict[str, Dict[date, float]] = {}
        last_trained: Dict[str, date] = {}

        for session in sessions:
            if not session.started_at:
                continue

            session_date = session.started_at.date()

            for muscle, load in (session.muscle_loads or {}).items():
                try:
                    numeric_load = float(load or 0)
                except (TypeError, ValueError):
                    continue

                if numeric_load <= 0:
                    continue

                muscle_total_load[muscle] = (
                    muscle_total_load.get(muscle, 0.0) + numeric_load
                )

                if muscle not in muscle_daily_load:
                    muscle_daily_load[muscle] = {}

                muscle_daily_load[muscle][session_date] = (
                    muscle_daily_load[muscle].get(session_date, 0.0) + numeric_load
                )

                previous_date = last_trained.get(muscle)

                if previous_date is None or session_date > previous_date:
                    last_trained[muscle] = session_date

        muscle_average_load: Dict[str, float] = {}

        for muscle, daily_loads in muscle_daily_load.items():
            muscle_average_load[muscle] = sum(daily_loads.values()) / window_days

        return {
            "sessions": sessions,
            "muscle_total_load": muscle_total_load,
            "muscle_average_load": muscle_average_load,
            "last_trained": last_trained,
        }

    @staticmethod
    def _recovery_recommendations(
        recovery_score: Optional[int],
        energy_score: Optional[int],
    ) -> List[Dict[str, Any]]:
        recommendations: List[Dict[str, Any]] = []

        if recovery_score is not None:
            if recovery_score < 40:
                recommendations.append(
                    {
                        "type": "recovery",
                        "id": "full_recovery",
                        "priority": "high",
                        "text": (
                            "Focus on recovery today and avoid "
                            "high-intensity training"
                        ),
                        "reason": {
                            "recovery_score": recovery_score,
                        },
                    }
                )

            elif recovery_score < 60:
                recommendations.append(
                    {
                        "type": "recovery",
                        "id": "light_training",
                        "priority": "medium",
                        "text": (
                            "Keep today's training light and " "focus on technique"
                        ),
                        "reason": {
                            "recovery_score": recovery_score,
                        },
                    }
                )

        if energy_score is not None and energy_score < 40:
            recommendations.append(
                {
                    "type": "recovery",
                    "id": "low_energy",
                    "priority": "medium",
                    "text": (
                        "Energy is low — prefer light activity " "or active recovery"
                    ),
                    "reason": {
                        "energy_score": energy_score,
                    },
                }
            )

        return recommendations

    @staticmethod
    def _habit_recommendations(
        habit_score: Optional[int],
    ) -> List[Dict[str, Any]]:
        if habit_score is None or habit_score >= 50:
            return []

        return [
            {
                "type": "habit",
                "id": "complete_habits",
                "priority": "medium",
                "text": ("Complete your recovery habits " "to improve recovery"),
                "reason": {
                    "habit_score": habit_score,
                },
            }
        ]

    @staticmethod
    def _training_recommendations(
        daily_load: Optional[float],
    ) -> List[Dict[str, Any]]:
        if daily_load is None:
            return []

        if daily_load >= 180:
            return [
                {
                    "type": "training",
                    "id": "very_high_daily_load",
                    "priority": "high",
                    "text": (
                        "Today's training load is very high. "
                        "Prioritize recovery before another hard session."
                    ),
                    "reason": {
                        "daily_load": round(daily_load, 2),
                    },
                }
            ]

        if daily_load >= 140:
            return [
                {
                    "type": "training",
                    "id": "high_daily_load",
                    "priority": "medium",
                    "text": (
                        "Today's training load is high. "
                        "Avoid adding unnecessary volume."
                    ),
                    "reason": {
                        "daily_load": round(daily_load, 2),
                    },
                }
            ]

        return []

    @staticmethod
    def _muscle_recommendations(
        muscle_total_load: Dict[str, float],
        muscle_average_load: Dict[str, float],
        last_trained: Dict[str, date],
        recovery_score: Optional[int],
        target_date: date,
    ) -> List[Dict[str, Any]]:
        recommendations: List[Dict[str, Any]] = []

        for muscle, recent_load in muscle_total_load.items():
            average_load = muscle_average_load.get(muscle, 0.0)

            relative_load = recent_load / average_load if average_load > 0 else 0.0

            last_training_date = last_trained.get(muscle)

            days_since_training = (
                (target_date - last_training_date).days
                if last_training_date is not None
                else 999
            )

            if (
                recent_load >= MUSCLE_HIGH_LOAD
                and days_since_training <= MUSCLE_TRAINING_RECOVERY_DAYS
            ):
                recommendations.append(
                    {
                        "type": "muscle",
                        "id": f"rest_{muscle}",
                        "muscle": muscle,
                        "priority": "high",
                        "text": (
                            f"Give {muscle} more recovery " "after heavy recent load"
                        ),
                        "reason": {
                            "recent_load": round(recent_load, 2),
                            "days_since": days_since_training,
                            "relative": round(relative_load, 2),
                        },
                    }
                )

                continue

            if recovery_score is not None and recovery_score < 45:
                continue

            if (
                recent_load < MUSCLE_LOW_LOAD
                or relative_load < 0.6
                or days_since_training >= MUSCLE_TRAINING_GAP_DAYS
            ):
                recommendations.append(
                    {
                        "type": "exercise",
                        "id": f"train_{muscle}",
                        "muscle": muscle,
                        "priority": "medium",
                        "text": (
                            f"Consider training {muscle} " "(lower recent volume)"
                        ),
                        "reason": {
                            "recent_load": round(recent_load, 2),
                            "days_since": days_since_training,
                            "relative": round(relative_load, 2),
                        },
                        "suggested_sets": 3,
                        "suggested_reps": "8-12",
                        "suggested_rpe": 7,
                    }
                )

        return recommendations

    @staticmethod
    def build_recommendations(
        user_id: int,
        sleep_score: Optional[int] = None,
        recovery_score: Optional[int] = None,
        energy_score: Optional[int] = None,
        habit_score: Optional[int] = None,
        daily_load: Optional[float] = None,
        target_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        target_date = target_date or date.today()

        recovery_data = RecommendationService._get_recovery_data(
            user_id=user_id,
            target_date=target_date,
        )

        if recovery_score is None:
            recovery_score = recovery_data.get("recovery_score")

        if sleep_score is None:
            sleep_score = recovery_data.get("sleep_score")

        if energy_score is None:
            energy_score = recovery_data.get("energy_score")

        if habit_score is None:
            habit_score = recovery_data.get("habit_score")

        if daily_load is None:
            daily_load = RecommendationService._get_daily_load(
                user_id=user_id,
                target_date=target_date,
            )

        context = RecommendationService._build_context(
            user_id=user_id,
            target_date=target_date,
            window_days=7,
        )

        recommendations: List[Dict[str, Any]] = []

        recommendations.extend(
            RecommendationService._recovery_recommendations(
                recovery_score=recovery_score,
                energy_score=energy_score,
            )
        )

        recommendations.extend(
            RecommendationService._habit_recommendations(
                habit_score=habit_score,
            )
        )

        recommendations.extend(
            RecommendationService._training_recommendations(
                daily_load=daily_load,
            )
        )

        recommendations.extend(
            RecommendationService._muscle_recommendations(
                muscle_total_load=context["muscle_total_load"],
                muscle_average_load=context["muscle_average_load"],
                last_trained=context["last_trained"],
                recovery_score=recovery_score,
                target_date=target_date,
            )
        )

        priority_order = {
            "high": 0,
            "medium": 1,
            "low": 2,
        }

        recommendations.sort(
            key=lambda recommendation: priority_order.get(
                recommendation.get("priority"),
                3,
            )
        )

        return recommendations[:MAX_RECOMMENDATIONS]
