from flask import Blueprint, render_template
from flask_login import login_required, current_user

from web.app.security import allow_barcode_scanner

nutrition_pages_bp = Blueprint("nutrition_pages", __name__, url_prefix="/nutrition")


@nutrition_pages_bp.get("/")
@login_required
def nutrition_page():
    allow_barcode_scanner()
    return render_template(
        "app/nutrition/nutrition.html",
        user=current_user,
        active="nutrition",
    )
