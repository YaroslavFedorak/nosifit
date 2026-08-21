from flask import Blueprint, jsonify
from flask_login import current_user, login_required

from myapp.app.services.dashboard.service import DashboardService
from myapp.app.services.recovery.recommendation_service import RecommendationService

dashboard_api_bp = Blueprint(
    "dashboard_api",
    __name__,
    url_prefix="/api/dashboard",
)


@dashboard_api_bp.get("/today")
@login_required
def today():
    data = DashboardService.get_today(current_user.id)
    return jsonify(data)


@dashboard_api_bp.get("/heatmap")
@login_required
def heatmap():
    data = DashboardService.get_heatmap(current_user.id)
    return jsonify(data)


@dashboard_api_bp.get("/day/<date_iso>")
@login_required
def day(date_iso):
    data = DashboardService.get_day(current_user.id, date_iso)

    if data is None:
        return jsonify({"error": "invalid_date_or_no_data"}), 404

    return jsonify(data)


@dashboard_api_bp.get("/recommendation")
@login_required
def recommendation():
    recommendations = RecommendationService.build_recommendations(current_user.id)

    if not recommendations:
        return jsonify({"recommendation": None})

    priority_order = {
        "high": 0,
        "medium": 1,
        "low": 2,
    }

    recommendation = min(
        recommendations,
        key=lambda item: (
            priority_order.get(
                item.get("priority"),
                3,
            )
            if isinstance(item, dict)
            else 3
        ),
    )

    return jsonify(
        {
            "recommendation": recommendation,
        }
    )
