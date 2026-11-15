from flask import Blueprint, jsonify, render_template
from flask_login import login_required, current_user

from backend.app.utils.profile_options import (
    ACTIVITIES,
    EXPERIENCES,
    GENDERS,
    GOALS,
    normalize_activity,
    normalize_experience,
    normalize_goal,
)
from web.app.routes.profile.connected_accounts import connected_accounts_context

profile_pages_bp = Blueprint("profile_pages", __name__, url_prefix="/profile")

TRAINING_LOCATIONS = ("gym", "home", "outdoor")


def account_summary(user) -> dict:
    """What the profile and settings screens of the /app interface show.

    The same facts the profile pages render on the server, as data: the
    account, the profile parameters, the choices of each field and the
    ways to sign in.
    """
    profile = user.profile
    return {
        "user": {
            "id": user.id,
            "name": user.username,
            "email": user.email,
            "member_since": user.created_at.date().isoformat() if user.created_at else None,
        },
        "profile": {
            "age": getattr(profile, "age", None),
            "gender": getattr(profile, "gender", None),
            "height": getattr(profile, "height", None),
            "weight": getattr(profile, "weight", None),
            "activity": normalize_activity(getattr(profile, "activity", None)),
            "goal": normalize_goal(getattr(profile, "goal", None)),
            "experience": normalize_experience(getattr(profile, "experience", None)),
            "workouts_per_week": getattr(profile, "workouts_per_week", None),
            "training_location": getattr(profile, "training_location", None),
            "wants_nutrition": bool(getattr(profile, "wants_nutrition", True)),
            "wants_recovery": bool(getattr(profile, "wants_recovery", True)),
        },
        "options": {
            "genders": list(GENDERS),
            "goals": list(GOALS),
            "activities": [list(pair) for pair in ACTIVITIES],
            "experiences": list(EXPERIENCES),
            "locations": list(TRAINING_LOCATIONS),
        },
        "sign_in": connected_accounts_context(user),
    }


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


@profile_pages_bp.get("/summary")
@login_required
def summary():
    return jsonify(account_summary(current_user))
