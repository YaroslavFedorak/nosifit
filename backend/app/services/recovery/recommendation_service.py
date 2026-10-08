from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from backend.app.models.recovery.daily_recovery_snapshot import (
    DailyRecoverySnapshot,
)
from backend.app.extensions import db
from backend.app.models.user import User
from backend.app.services.recovery.constants import MAX_RECOMMENDATIONS
from backend.app.services.training.model import TrainingModelService
from backend.app.services.training.model import parameters as training_parameters


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
    def _training_analysis(user_id: int, target_date: date):
        user = db.session.get(User, user_id)
        if user is None:
            return None
        return TrainingModelService.analyse_user(user, target_date)

    @staticmethod
    def _day_stress(user_id: int, target_date: date) -> Optional[Dict[str, Any]]:
        try:
            return TrainingModelService.day_stress(user_id, target_date)
        except Exception:
            return None

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
                        "title_key": "recommendations.recovery.fullRecovery.title",
                        "message_key": "recommendations.recovery.fullRecovery.message",
                        "params": {
                            "score": recovery_score,
                        },
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
                        "title_key": "recommendations.recovery.lightTraining.title",
                        "message_key": "recommendations.recovery.lightTraining.message",
                        "params": {
                            "score": recovery_score,
                        },
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
                    "title_key": "recommendations.recovery.lowEnergy.title",
                    "message_key": "recommendations.recovery.lowEnergy.message",
                    "params": {
                        "score": energy_score,
                    },
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
                "title_key": "recommendations.recovery.completeHabits.title",
                "message_key": "recommendations.recovery.completeHabits.message",
                "params": {
                    "score": habit_score,
                },
                "reason": {
                    "habit_score": habit_score,
                },
            }
        ]

    @staticmethod
    def _training_recommendations(
        day_stress: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """A day far above the user's typical session (stress proxy) earns a
        recovery note. Relative to the user's own baseline, not a fixed load."""
        if not day_stress or day_stress.get("session_training_stress_proxy", 0) <= 0:
            return []

        ratio = day_stress["session_training_stress_proxy"] / day_stress["typical"]
        thresholds = training_parameters.HIGH_DAY_STRESS_RATIOS
        reason = {
            "session_training_stress_proxy": day_stress["session_training_stress_proxy"],
            "typical_session": day_stress["typical"],
        }
        params = {"hard_sets": day_stress.get("hard_sets", 0)}

        if ratio >= thresholds["very_high"]:
            return [
                {
                    "type": "training",
                    "id": "very_high_daily_load",
                    "priority": "high",
                    "title_key": "recommendations.recovery.veryHighLoad.title",
                    "message_key": "recommendations.recovery.veryHighLoad.message",
                    "params": params,
                    "reason": reason,
                }
            ]

        if ratio >= thresholds["high"]:
            return [
                {
                    "type": "training",
                    "id": "high_daily_load",
                    "priority": "medium",
                    "title_key": "recommendations.recovery.highLoad.title",
                    "message_key": "recommendations.recovery.highLoad.message",
                    "params": params,
                    "reason": reason,
                }
            ]

        return []

    @staticmethod
    def _muscle_recommendations(
        analysis,
        recovery_score: Optional[int],
    ) -> List[Dict[str, Any]]:
        """Rest notes for fatigued muscles and train notes for Stage 1 targets."""
        if analysis is None:
            return []

        recommendations: List[Dict[str, Any]] = []
        statuses = analysis.statuses

        for plan in analysis.plans:
            status = statuses[plan.muscle]
            reason = {
                "state": status.state,
                "readiness": status.readiness_level,
                "weekly_sets": round(status.exposure_smoothed, 1),
            }

            if plan.action == "rest":
                recommendations.append(
                    {
                        "type": "muscle",
                        "id": f"rest_{plan.muscle}",
                        "muscle": plan.muscle,
                        "priority": "high",
                        "title_key": "recommendations.recovery.muscleRest.title",
                        "message_key": "recommendations.recovery.muscleRest.message",
                        "params": {"muscle": plan.muscle},
                        "reason": reason,
                    }
                )
                continue

            # A low overall recovery score suppresses suggestions to add work.
            if recovery_score is not None and recovery_score < 45:
                continue

            if plan.action == "prioritize":
                recommendations.append(
                    {
                        "type": "exercise",
                        "id": f"train_{plan.muscle}",
                        "muscle": plan.muscle,
                        "priority": "medium",
                        "title_key": "recommendations.recovery.muscleTraining.title",
                        "message_key": "recommendations.recovery.muscleTraining.message",
                        "params": {"muscle": plan.muscle},
                        "suggested_sets": plan.allocated_sets,
                        "reason": reason,
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

        # ``daily_load`` (legacy number) is accepted for compatibility but no
        # longer used: training notes come from the training model.
        try:
            analysis = RecommendationService._training_analysis(user_id, target_date)
        except Exception:
            analysis = None

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
                RecommendationService._day_stress(user_id, target_date),
            )
        )

        recommendations.extend(
            RecommendationService._muscle_recommendations(
                analysis,
                recovery_score=recovery_score,
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
