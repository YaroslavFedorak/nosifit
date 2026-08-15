from flask import Blueprint, jsonify
from myapp.app.services.dashboard.dashboard_service import get_dashboard

dashboard_bp = Blueprint("dashboard_api", __name__, url_prefix="/api/dashboard")


@dashboard_bp.get("/<int:user_id>")
def dashboard(user_id):
    data = get_dashboard(user_id)
    return jsonify(data)
