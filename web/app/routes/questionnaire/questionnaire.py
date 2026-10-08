from flask import Blueprint, flash, redirect, request, url_for
from flask_login import current_user, login_required

from backend.app.extensions import db
from backend.app.models.user_profile import UserProfile

questionnaire_bp = Blueprint("questionnaire", __name__, url_prefix="/questionnaire")

# Body regions offered by the form; the training model maps them to muscles.
WEAK_POINT_CHOICES = ("chest", "back", "legs", "core", "lower_back")
STRONG_POINT_CHOICES = ("chest", "back", "legs", "core")
ENVIRONMENT_CHOICES = ("gym", "home", "outdoor")


def _choices(field, allowed):
    """Checked values of a multi-checkbox field, restricted to ``allowed``."""
    values = []
    for value in request.form.getlist(field):
        key = (value or "").strip().lower()
        if key in allowed and key not in values:
            values.append(key)
    return values


@questionnaire_bp.post("/")
@login_required
def save_questionnaire():
    user = current_user
    environment = (request.form.get("environment") or "").strip().lower()

    user.weak_points = _choices("weak_points", WEAK_POINT_CHOICES)
    user.strong_points = _choices("strong_points", STRONG_POINT_CHOICES)

    if environment in ENVIRONMENT_CHOICES:
        user.environment = environment
        profile = UserProfile.query.filter_by(user_id=user.id).first()
        if profile is not None:
            profile.training_location = environment

    db.session.commit()
    flash("Анкету збережено", "success")
    return redirect(url_for("questionnaire_pages.questionnaire_page"))
