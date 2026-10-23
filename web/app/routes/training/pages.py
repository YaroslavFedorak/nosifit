from flask import Blueprint, render_template
from flask_login import login_required, current_user

from backend.app.services.training import catalog_service

training_pages_bp = Blueprint("training_pages", __name__, url_prefix="/training")


@training_pages_bp.get("/")
@login_required
def training_page():
    return render_template(
        "app/training/training.html",
        user=current_user,
        active="training",
        exercise_muscles=catalog_service.primary_muscles(),
    )
