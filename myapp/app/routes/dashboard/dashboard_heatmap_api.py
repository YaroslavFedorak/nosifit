from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from myapp.app.services.dashboard.aggregator import (
    get_today_overview,
    get_heatmap,
)

dashboard_heatmap_api_bp = Blueprint(
    "dashboard_heatmap_api", __name__, url_prefix="/api/dashboard"
)


@dashboard_heatmap_api_bp.get("/today")
@login_required
def today():
    return jsonify(get_today_overview(current_user.id))


@dashboard_heatmap_api_bp.get("/heatmap")
@login_required
def heatmap():
    return jsonify(get_heatmap(current_user.id))
