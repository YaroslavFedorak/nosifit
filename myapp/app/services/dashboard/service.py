from .aggregator import get_today_overview, get_heatmap
from .day import get_day_details


class DashboardService:
    @staticmethod
    def get_today(user_id):
        return get_today_overview(user_id)

    @staticmethod
    def get_heatmap(user_id):
        return get_heatmap(user_id)

    @staticmethod
    def get_day(user_id, day_iso):
        return get_day_details(user_id, day_iso)
