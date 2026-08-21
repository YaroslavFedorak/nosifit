from flask import Blueprint, jsonify
from flask_login import current_user, login_required

from myapp.app.services.dashboard.day import get_day_details

dashboard_day_api_bp = Blueprint(
    "dashboard_day_api",
    __name__,
    url_prefix="/api/dashboard",
)


@dashboard_day_api_bp.get("/day/<date_iso>")
@login_required
def day(date_iso):
    data = get_day_details(
        current_user.id,
        date_iso,
    )

    if data is None:
        return (
            jsonify(
                {
                    "error": "invalid_date_or_no_data",
                }
            ),
            404,
        )

    return jsonify(data)
