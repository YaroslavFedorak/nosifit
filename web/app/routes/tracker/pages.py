from flask import Blueprint, render_template
from flask_login import login_required, current_user

tracker_pages_bp = Blueprint("tracker_pages", __name__, url_prefix="/tracker")


@tracker_pages_bp.get("/")
@login_required
def tracker_page():
    return render_template(
        "app/tracker.html",
        user=current_user,
        active="tracker",
    )
