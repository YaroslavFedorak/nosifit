from flask import Blueprint, render_template
from flask_login import login_required, current_user

equipment_pages_bp = Blueprint("equipment_pages", __name__, url_prefix="/equipment")


@equipment_pages_bp.get("/")
@login_required
def equipment_page():
    return render_template(
        "app/equipment.html",
        user=current_user,
        active="equipment",
    )
