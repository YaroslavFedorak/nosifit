from flask import Blueprint, jsonify
from myapp.app.services.dashboard.dashboard_service import get_dashboard

dashboard_api_bp = Blueprint("dashboard_api", __name__, url_prefix="/api/dashboard")


@dashboard_api_bp.get("/<int:user_id>")
def dashboard_api(user_id):
    data = get_dashboard(user_id)
    return jsonify(data)
