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
    try:
        data = RecommendationService.build_recommendations(current_user.id) or []
    except Exception:
        return jsonify({"recommendation": None})

    top = None
    if isinstance(data, list) and data:
        try:
            top = sorted(
                data,
                key=lambda x: x.get("priority", 0),
                reverse=True,
            )[0]
        except Exception:
            top = data[0]

    return jsonify({"recommendation": top})
