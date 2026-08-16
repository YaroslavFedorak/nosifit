from flask import Blueprint, render_template
from flask_login import login_required, current_user

profile_view_bp = Blueprint("profile_view", __name__)


@profile_view_bp.route("/")
@login_required
def profile_page():
    return render_template(
        "app/profile/profile.html",
        user=current_user,
        profile=current_user.profile,
        active="profile",
    )
