from flask import Blueprint, render_template
from flask_login import login_required, current_user

training_plan_pages_bp = Blueprint(
    "training_plan_pages",
    __name__,
    url_prefix="/training_plan",
)


@training_plan_pages_bp.get("/")
@login_required
def training_plan_page():
    return render_template(
        "app/training_plan.html",
        user=current_user,
        active="training_plan",
    )
