from flask import Blueprint, render_template
from flask_login import login_required, current_user

recovery_pages_bp = Blueprint("recovery_pages", __name__, url_prefix="/recovery")


@recovery_pages_bp.get("/")
@login_required
def recovery_page():
    return render_template(
        "app/recovery/recovery.html",
        user=current_user,
        active="recovery",
    )
