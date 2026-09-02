from flask import Blueprint, render_template
from flask_login import login_required, current_user

profile_pages_bp = Blueprint("profile_pages", __name__, url_prefix="/profile")


@profile_pages_bp.get("/")
@login_required
def profile_page():
    return render_template(
        "app/profile/profile.html",
        user=current_user,
        profile=current_user.profile,
        active="profile",
    )
