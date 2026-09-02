from flask import Blueprint, request, redirect, url_for, flash
from flask_login import login_required, current_user
from web.app import db

profile_update_bp = Blueprint("profile_update", __name__)


@profile_update_bp.route("/profile/update_full", methods=["POST"])
@login_required
def update_full():
    user = current_user
    profile = current_user.profile

    # Helpers
    def to_float(v):
        return float(v) if v not in (None, "", " ") else None

    def to_int(v):
        return int(v) if v not in (None, "", " ") else None

    # User fields
    user.username = request.form.get("username")
    user.email = request.form.get("email")

    # UserProfile fields
    profile.age = to_int(request.form.get("age"))
    profile.height = to_float(request.form.get("height"))
    profile.weight = to_float(request.form.get("weight"))
    profile.gender = request.form.get("gender") or None
    profile.activity = request.form.get("activity") or None
    profile.goal = request.form.get("goal") or None
    profile.experience = request.form.get("experience") or None
    profile.workouts_per_week = to_int(request.form.get("workouts_per_week"))

    profile.training_location = request.form.get("training_location") or None
    profile.wants_nutrition = bool(int(request.form.get("wants_nutrition", 0)))
    profile.wants_recovery = bool(int(request.form.get("wants_recovery", 0)))
    profile.onboarding_completed = bool(
        int(request.form.get("onboarding_completed", 0))
    )

    db.session.commit()

    return redirect("/profile")


@profile_update_bp.route("/profile/change_email", methods=["POST"])
@login_required
def change_email():
    new_email = request.form.get("new_email")
    password = request.form.get("password")

    if not current_user.check_password(password):
        flash("Невірний пароль", "error")
        return redirect(url_for("dashboard.profile_page"))

    current_user.email = new_email
    db.session.commit()

    flash("Email оновлено", "success")
    return redirect(url_for("dashboard.profile_page"))


@profile_update_bp.route("/profile/change_password", methods=["POST"])
@login_required
def change_password():
    current_password = request.form.get("current_password")
    new_password = request.form.get("new_password")

    if not current_user.check_password(current_password):
        flash("Невірний пароль", "error")
        return redirect(url_for("dashboard.profile_page"))

    current_user.set_password(new_password)
    db.session.commit()

    flash("Пароль змінено", "success")
    return redirect(url_for("dashboard.profile_page"))


@profile_update_bp.route("/profile/delete_account", methods=["POST"])
@login_required
def delete_account():
    confirm_email = request.form.get("confirm_email")
    password = request.form.get("password")

    if confirm_email != current_user.email:
        flash("Email не співпадає", "error")
        return redirect(url_for("dashboard.profile_page"))

    if not current_user.check_password(password):
        flash("Невірний пароль", "error")
        return redirect(url_for("dashboard.profile_page"))

    db.session.delete(current_user)
    db.session.commit()

    flash("Акаунт видалено", "success")
    return redirect(url_for("auth.login"))
