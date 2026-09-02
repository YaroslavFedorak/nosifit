from flask import Blueprint, render_template
from flask_login import login_required, current_user

questionnaire_bp = Blueprint("questionnaire", __name__, url_prefix="/questionnaire")


@questionnaire_bp.get("/")
@login_required
def questionnaire_page():
    return render_template(
        "app/questionnaire.html",
        user=current_user,
        active="questionnaire",
    )
