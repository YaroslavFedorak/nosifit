from flask import Blueprint, current_app, request, redirect, url_for, flash
from flask_login import login_required, current_user

from backend.app.extensions import db
from backend.app.utils.validation import (
    ValidationError,
    clean_choice,
    clean_username,
    parse_profile_number,
)

from backend.app.services.nutrition.calories_service import (
    update_user_nutrition_goals,
)

profile_update_bp = Blueprint(
    "profile_update",
    __name__,
)


def _flag(name, current):
    """Boolean form field; a field the form did not send keeps its value."""
    if name not in request.form:
        return bool(current)
    return request.form.get(name) in ("1", "true", "on")


@profile_update_bp.route(
    "/profile/update_full",
    methods=["POST"],
)
@login_required
def update_full():
    user = current_user
    profile = user.profile

    if profile is None:
        flash("Не вдалося оновити профіль", "error")
        return redirect(url_for("profile_pages.profile_page"))

    try:
        username = clean_username(request.form.get("username"))
        if not username:
            raise ValidationError("username")

        # Email is changed only through /profile/change_email, which proves
        # ownership of the new address with a code. Accepting it here let any
        # session claim an arbitrary unregistered address.
        submitted_email = (request.form.get("email") or "").strip().lower()
        if submitted_email and submitted_email != user.email.lower():
            flash("Щоб змінити email, скористайтеся кнопкою «Змінити email».", "error")
            return redirect(url_for("profile_pages.profile_page"))

        values = {
            "age": parse_profile_number("age", request.form.get("age")),
            "height": parse_profile_number("height", request.form.get("height")),
            "weight": parse_profile_number("weight", request.form.get("weight")),
            "workouts_per_week": parse_profile_number(
                "workouts_per_week", request.form.get("workouts_per_week")
            ),
            "gender": clean_choice("gender", request.form.get("gender")),
            "activity": clean_choice("activity", request.form.get("activity")),
            "goal": clean_choice("goal", request.form.get("goal")),
            "experience": clean_choice("experience", request.form.get("experience")),
            "training_location": clean_choice(
                "training_location", request.form.get("training_location")
            )
            or profile.training_location
            or "home",
        }
    except ValidationError:
        flash(
            "Перевірте дані профілю",
            "error",
        )
        return redirect(url_for("profile_pages.profile_page"))

    try:
        user.username = username
        for field, value in values.items():
            setattr(profile, field, value)

        profile.wants_nutrition = _flag("wants_nutrition", profile.wants_nutrition)
        profile.wants_recovery = _flag("wants_recovery", profile.wants_recovery)
        profile.onboarding_completed = _flag("onboarding_completed", profile.onboarding_completed)

        # Save the updated profile first.
        db.session.commit()

        # Recalculate nutrition goals using
        # the newly saved profile parameters.
        update_user_nutrition_goals(user)

        flash(
            "Профіль оновлено",
            "success",
        )

    except Exception:
        db.session.rollback()
        current_app.logger.exception("Profile update failed")

        flash(
            "Не вдалося оновити профіль",
            "error",
        )

    return redirect(url_for("profile_pages.profile_page"))
