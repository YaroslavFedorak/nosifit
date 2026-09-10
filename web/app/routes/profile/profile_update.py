from flask import Blueprint, request, redirect, url_for, flash
from flask_login import login_required, current_user

from web.app import db

from web.app.services.nutrition.calories_service import (
    update_user_nutrition_goals,
)

profile_update_bp = Blueprint(
    "profile_update",
    __name__,
)


def to_float(value):
    if value in (None, "", " "):
        return None

    return float(value)


def to_int(value):
    if value in (None, "", " "):
        return None

    return int(value)


@profile_update_bp.route(
    "/profile/update_full",
    methods=["POST"],
)
@login_required
def update_full():
    user = current_user
    profile = user.profile

    try:
        user.username = request.form.get("username")

        user.email = request.form.get("email")

        profile.age = to_int(request.form.get("age"))

        profile.height = to_float(request.form.get("height"))

        profile.weight = to_float(request.form.get("weight"))

        profile.gender = request.form.get("gender") or None

        profile.activity = request.form.get("activity") or None

        profile.goal = request.form.get("goal") or None

        profile.experience = request.form.get("experience") or None

        profile.workouts_per_week = to_int(request.form.get("workouts_per_week"))

        profile.training_location = request.form.get("training_location") or None

        profile.wants_nutrition = bool(
            int(
                request.form.get(
                    "wants_nutrition",
                    0,
                )
            )
        )

        profile.wants_recovery = bool(
            int(
                request.form.get(
                    "wants_recovery",
                    0,
                )
            )
        )

        profile.onboarding_completed = bool(
            int(
                request.form.get(
                    "onboarding_completed",
                    0,
                )
            )
        )

        # Save the updated profile first.
        db.session.commit()

        # Recalculate nutrition goals using
        # the newly saved profile parameters.
        update_user_nutrition_goals(user)

        flash(
            "Профіль оновлено",
            "success",
        )

    except (TypeError, ValueError):
        db.session.rollback()

        flash(
            "Некоректні дані профілю",
            "error",
        )

    except Exception:
        db.session.rollback()

        flash(
            "Не вдалося оновити профіль",
            "error",
        )

    return redirect(url_for("profile_pages.profile_page"))


@profile_update_bp.route(
    "/profile/change_email",
    methods=["POST"],
)
@login_required
def change_email():
    new_email = (request.form.get("new_email") or "").strip()

    password = request.form.get("password")

    if not current_user.check_password(password):
        flash(
            "Невірний пароль",
            "error",
        )

        return redirect(url_for("profile_pages.profile_page"))

    if not new_email:
        flash(
            "Email не може бути порожнім",
            "error",
        )

        return redirect(url_for("profile_pages.profile_page"))

    current_user.email = new_email

    db.session.commit()

    flash(
        "Email оновлено",
        "success",
    )

    return redirect(url_for("profile_pages.profile_page"))


@profile_update_bp.route(
    "/profile/delete_account",
    methods=["POST"],
)
@login_required
def delete_account():
    confirm_email = request.form.get("confirm_email")

    password = request.form.get("password")

    if confirm_email != current_user.email:
        flash(
            "Email не співпадає",
            "error",
        )

        return redirect(url_for("profile_pages.profile_page"))

    if not current_user.check_password(password):
        flash(
            "Невірний пароль",
            "error",
        )

        return redirect(url_for("profile_pages.profile_page"))

    db.session.delete(current_user)
    db.session.commit()

    flash(
        "Акаунт видалено",
        "success",
    )

    return redirect(url_for("auth.login"))
