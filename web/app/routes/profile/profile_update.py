from flask import Blueprint, current_app, jsonify, request, redirect, url_for, flash
from flask_login import login_required, current_user

from backend.app.extensions import db
from backend.app.utils.validation import (
    ValidationError,
    clean_choice,
    clean_username,
    parse_account_age,
    parse_profile_number,
)

from backend.app.services.nutrition.calories_service import (
    update_user_nutrition_goals,
)

profile_update_bp = Blueprint(
    "profile_update",
    __name__,
)


def _wants_json() -> bool:
    """The /app interface asks for JSON; the profile form gets its redirect."""
    best = request.accept_mimetypes.best_match(["text/html", "application/json"])
    return best == "application/json"


def _answer(message, category, code, status=200):
    """A flash and a redirect for the form, the same outcome as JSON for a script."""
    if _wants_json():
        if category == "success":
            # Imported here: the pages module imports this package's blueprints.
            from web.app.routes.profile.pages import account_summary

            return jsonify({"status": "ok", "account": account_summary(current_user)})
        return jsonify({"status": "error", "message": code}), status
    flash(message, category)
    return redirect(url_for("profile_pages.profile_page"))


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
        return _answer("Не вдалося оновити профіль", "error", "no_profile", 400)

    try:
        username = clean_username(request.form.get("username"))
        if not username:
            raise ValidationError("username")

        # Email is changed only through /profile/change_email, which proves
        # ownership of the new address with a code. Accepting it here let any
        # session claim an arbitrary unregistered address.
        submitted_email = (request.form.get("email") or "").strip().lower()
        if submitted_email and submitted_email != user.email.lower():
            return _answer(
                "Щоб змінити email, скористайтеся кнопкою «Змінити email».",
                "error",
                "email_not_changed_here",
                400,
            )

        values = {
            "age": parse_account_age(request.form.get("age")),
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
        return _answer("Перевірте дані профілю", "error", "invalid_profile", 400)

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

    except Exception:
        db.session.rollback()
        current_app.logger.exception("Profile update failed")
        return _answer("Не вдалося оновити профіль", "error", "save_failed", 500)

    return _answer("Профіль оновлено", "success", "ok")
