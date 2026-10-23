from flask import Blueprint, render_template
from flask_login import login_required, current_user

from web.app.routes.profile.connected_accounts import connected_accounts_context

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


@profile_pages_bp.get("/account")
@login_required
def account_page():
    """Personal details, sign-in methods, email, password, data and account deletion."""
    return render_template(
        "app/profile/account.html",
        user=current_user,
        profile=current_user.profile,
        active="profile",
        connected=connected_accounts_context(current_user),
    )
