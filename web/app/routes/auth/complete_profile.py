from flask import Blueprint, render_template, request, redirect, session
from flask_login import login_user
from web.app import db
from web.app.models.user import User

complete_profile_bp = Blueprint("complete_profile", __name__, url_prefix="/auth")


@complete_profile_bp.route("/complete_profile", methods=["GET", "POST"])
def complete_profile():
    oauth_user = session.get("oauth_user")

    if not oauth_user:
        return redirect("/auth/login")

    existing_user = User.query.filter_by(email=oauth_user["email"]).first()
    if existing_user:
        login_user(existing_user)
        session.pop("oauth_user")
        return redirect("/profile")

    if request.method == "POST":
        age = int(request.form.get("age"))
        height = float(request.form.get("height"))
        weight = float(request.form.get("weight"))
        gender = request.form.get("gender")
        activity = float(request.form.get("activity"))
        goal = request.form.get("goal")
        experience = request.form.get("experience")
        workouts = int(request.form.get("workouts"))

        user = User(
            username=oauth_user["name"],
            email=oauth_user["email"],
            password="oauth",
            age=age,
            height=height,
            weight=weight,
            gender=gender,
            activity=activity,
            goal=goal,
            experience=experience,
            workouts_per_week=workouts,
            is_premium=False,
        )

        db.session.add(user)
        db.session.commit()

        from flask_login import logout_user

        logout_user()
        login_user(user, remember=True)
        session.pop("oauth_user")

        return redirect("/profile")

    return render_template("auth/complete_profile.html", oauth_user=oauth_user)
