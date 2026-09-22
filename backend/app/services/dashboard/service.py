from backend.app.dashboard.recommendations.service import (
    DashboardRecommendationService,
)
from backend.app.services.dashboard.aggregator import (
    get_heatmap,
    get_today_overview,
)
from backend.app.services.dashboard.day import (
    get_day_details,
)


class DashboardService:
    @staticmethod
    def get_today(user_id):
        return get_today_overview(user_id)

    @staticmethod
    def get_heatmap(user_id):
        return get_heatmap(user_id)

    @staticmethod
    def get_day(user_id, date):
        return get_day_details(
            user_id,
            date,
        )

    @staticmethod
    def get_recommendation(user_id):
        return DashboardRecommendationService.get_recommendations(
            user_id,
        )

