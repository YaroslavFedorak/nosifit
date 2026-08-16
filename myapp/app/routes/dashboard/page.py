from flask import Blueprint, render_template
from flask_login import login_required

dashboard_page_bp = Blueprint("dashboard_page", __name__, url_prefix="/dashboard")


@dashboard_page_bp.get("")
@login_required
def dashboard_page():
    return render_template("app/dashboard/dashboard.html")
