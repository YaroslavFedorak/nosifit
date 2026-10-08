from flask import Blueprint, render_template
from flask_login import login_required, current_user

training_explanation_bp = Blueprint(
    "training_explanation",
    __name__,
    url_prefix="/training_explanation",
)


@training_explanation_bp.get("/")
@login_required
def training_explanation_page():
    return render_template(
        "app/training/explanation.html",
        user=current_user,
        active="training_explanation",
    )
