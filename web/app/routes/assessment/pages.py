from flask import Blueprint, render_template
from flask_login import login_required, current_user

assessment_pages_bp = Blueprint("assessment_pages", __name__, url_prefix="/assessment")


@assessment_pages_bp.get("/")
@login_required
def assessment_page():
    return render_template(
        "app/assessment.html",
        user=current_user,
        active="assessment",
    )
