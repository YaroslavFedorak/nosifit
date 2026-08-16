from flask import Blueprint, render_template
from flask_login import login_required, current_user

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_bp.get("/")
@login_required
def dashboard():
    return render_template(
        "app/dashboard/dashboard.html",
        user=current_user,
        active="dashboard",
    )
