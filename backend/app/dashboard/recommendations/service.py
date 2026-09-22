from datetime import date
from typing import Any, Iterable, Optional

from backend.app.dashboard.recommendations.dto import (
    DashboardRecommendations,
    PRIORITY_VALUES,
    Recommendation,
)
from backend.app.services.nutrition.recommendation_service import (
    get_nutrition_recommendations,
)
from backend.app.services.recovery.recommendation_service import (
    RecommendationService,
)
from backend.app.training.training_analysis.recommendations_engine import (
    build_recommendations as build_training_recommendations,
)


class DashboardRecommendationService:
    TRAINING_CATEGORY = "training"
    RECOVERY_CATEGORY = "recovery"
    NUTRITION_CATEGORY = "nutrition"

    @staticmethod
    def _priority_value(priority: Optional[str]) -> int:
        return PRIORITY_VALUES.get(
            str(priority).lower(),
            0,
        )

    @staticmethod
    def _normalize_priority(
        priority: Any,
        default: str = "medium",
    ) -> str:
        value = str(priority or default).lower().strip()

        if value in PRIORITY_VALUES:
            return value

        return default

    @staticmethod
    def _make_recommendation(
        category: str,
        item: dict[str, Any],
        index: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        recommendation_type: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Optional[Recommendation]:
        if not isinstance(item, dict):
            return None

        item_id = (
            item.get("id")
            or item.get("exercise_id")
            or item.get("type")
            or f"{category}_{index}"
        )

        item_title = (
            title
            or item.get("title")
            or item.get("name")
            or item.get("exercise")
            or item.get("type")
        )

        item_description = (
            description
            or item.get("description")
            or item.get("message")
            or item.get("text")
            or ""
        )

        if not item_title:
            return None

        item_priority = DashboardRecommendationService._normalize_priority(
            item.get("priority"),
        )

        item_type = recommendation_type or item.get("type")
        item_reason = reason or item.get("reason")

        suggested_sets = item.get("suggested_sets")
        suggested_reps = item.get("suggested_reps")
        suggested_rpe = item.get("suggested_rpe")

        score = item.get("score", 0.0)

        try:
            score = float(score)
        except (TypeError, ValueError):
            score = 0.0

        return Recommendation(
            category=category,
            id=str(item_id),
            title=str(item_title),
            description=str(item_description),
            priority=item_priority,
            type=(str(item_type) if item_type is not None else None),
            reason=(str(item_reason) if item_reason is not None else None),
            suggested_sets=(
                int(suggested_sets) if suggested_sets is not None else None
            ),
            suggested_reps=(
                int(suggested_reps) if suggested_reps is not None else None
            ),
            suggested_rpe=(float(suggested_rpe) if suggested_rpe is not None else None),
            score=score,
        )

    @staticmethod
    def _training_candidates(
        user: Any,
        sessions: list,
        target_day: date,
    ) -> list[Recommendation]:
        try:
            package = build_training_recommendations(
                user=user,
                sessions=sessions,
                target_day=target_day,
            )
        except Exception:
            return []

        candidates: list[Recommendation] = []

        recommended_exercises = package.get(
            "recommended_exercises",
            [],
        )

        for index, item in enumerate(recommended_exercises):
            if not isinstance(item, dict):
                continue

            exercise_name = item.get("exercise")

            if not exercise_name:
                continue

            reasons = item.get("reasons") or []

            if isinstance(reasons, str):
                reasons = [reasons]

            reason_text = str(reasons[0]) if reasons else None

            description = (
                reason_text
                or package.get("summary")
                or "Recommended based on your recent training."
            )

            recommendation = DashboardRecommendationService._make_recommendation(
                category=DashboardRecommendationService.TRAINING_CATEGORY,
                item=item,
                index=index,
                title=str(exercise_name),
                description=description,
                recommendation_type="exercise",
                reason=reason_text,
            )

            if recommendation is not None:
                candidates.append(recommendation)

        return candidates

    @staticmethod
    def _recovery_candidates(
        user_id: int,
    ) -> list[Recommendation]:
        try:
            raw = RecommendationService.build_recommendations(
                user_id,
            )
        except Exception:
            return []

        if not raw:
            return []

        candidates: list[Recommendation] = []

        for index, item in enumerate(raw):
            if not isinstance(item, dict):
                continue

            recommendation_type = str(
                item.get("type") or "",
            ).lower()

            if recommendation_type in {
                "training",
                "exercise",
                "muscle",
                "very_high_daily_load",
                "high_daily_load",
            }:
                continue

            recommendation = DashboardRecommendationService._make_recommendation(
                category=DashboardRecommendationService.RECOVERY_CATEGORY,
                item=item,
                index=index,
            )

            if recommendation is not None:
                candidates.append(recommendation)

        return candidates

    @staticmethod
    def _nutrition_candidates(
        user_id: int,
    ) -> list[Recommendation]:
        try:
            data = get_nutrition_recommendations(
                user_id,
            )
        except Exception:
            return []

        if not isinstance(data, dict):
            return []

        raw = data.get("recommendations") or []

        candidates: list[Recommendation] = []

        for index, item in enumerate(raw):
            recommendation = DashboardRecommendationService._make_recommendation(
                category=DashboardRecommendationService.NUTRITION_CATEGORY,
                item=item,
                index=index,
            )

            if recommendation is not None:
                candidates.append(recommendation)

        return candidates

    @staticmethod
    def _sort_candidates(
        candidates: Iterable[Recommendation],
    ) -> list[Recommendation]:
        return sorted(
            candidates,
            key=lambda item: (
                DashboardRecommendationService._priority_value(
                    item.priority,
                ),
                item.score,
            ),
            reverse=True,
        )

    @staticmethod
    def _select_category(
        candidates: list[Recommendation],
    ) -> Optional[Recommendation]:
        if not candidates:
            return None

        return DashboardRecommendationService._sort_candidates(
            candidates,
        )[0]

    @staticmethod
    def _daily_score(
        recommendation: Recommendation,
    ) -> float:
        priority_score = (
            DashboardRecommendationService._priority_value(
                recommendation.priority,
            )
            * 100
        )

        return priority_score + recommendation.score

    @staticmethod
    def _select_daily(
        categories: list[Recommendation],
    ) -> Optional[Recommendation]:
        if not categories:
            return None

        return max(
            categories,
            key=DashboardRecommendationService._daily_score,
        )

    @staticmethod
    def get_recommendations(
        user_id: int,
        target_day: Optional[date] = None,
        user: Any = None,
        sessions: Optional[list] = None,
    ) -> dict[str, Any]:
        if target_day is None:
            target_day = date.today()

        if user is None:
            from backend.app.models.user import User

            user = User.query.get(user_id)

        if sessions is None:
            from backend.app.models.training_session import TrainingSession

            sessions = TrainingSession.query.filter(
                TrainingSession.user_id == user_id,
            ).all()

        training = DashboardRecommendationService._select_category(
            DashboardRecommendationService._training_candidates(
                user=user,
                sessions=sessions,
                target_day=target_day,
            ),
        )

        recovery = DashboardRecommendationService._select_category(
            DashboardRecommendationService._recovery_candidates(
                user_id,
            ),
        )

        nutrition = DashboardRecommendationService._select_category(
            DashboardRecommendationService._nutrition_candidates(
                user_id,
            ),
        )

        category_recommendations = [
            recommendation
            for recommendation in (
                training,
                recovery,
                nutrition,
            )
            if recommendation is not None
        ]

        daily = DashboardRecommendationService._select_daily(
            category_recommendations,
        )

        result = DashboardRecommendations(
            daily=daily,
            training=training,
            recovery=recovery,
            nutrition=nutrition,
        )

        return result.to_dict()

    @staticmethod
    def get_daily_recommendation(
        user_id: int,
        target_day: Optional[date] = None,
    ) -> Optional[dict[str, Any]]:
        data = DashboardRecommendationService.get_recommendations(
            user_id=user_id,
            target_day=target_day,
        )

        return data.get("daily")

    @staticmethod
    def get_category_recommendation(
        user_id: int,
        category: str,
        target_day: Optional[date] = None,
    ) -> Optional[dict[str, Any]]:
        data = DashboardRecommendationService.get_recommendations(
            user_id=user_id,
            target_day=target_day,
        )

        categories = data.get("categories") or {}

        return categories.get(
            str(category).lower(),
        )

