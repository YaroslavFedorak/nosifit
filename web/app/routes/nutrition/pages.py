from flask import Blueprint, render_template
from flask_login import login_required, current_user

nutrition_pages_bp = Blueprint("nutrition_pages", __name__, url_prefix="/nutrition")


@nutrition_pages_bp.get("/")
@login_required
def nutrition_page():
    return render_template(
        "app/nutrition/nutrition.html",
        user=current_user,
        active="nutrition",
    )
