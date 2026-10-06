from flask import Blueprint, render_template, request, redirect, session, flash
from flask_login import login_user

from backend.app.extensions import db
from backend.app.models.user import User
from backend.app.models.oauth_account import OAuthAccount
from backend.app.models.user_profile import UserProfile

complete_profile_bp = Blueprint(
    "complete_profile",
    __name__,
    url_prefix="/auth",
)


def _link_oauth_account(user, oauth_user):
    exists = OAuthAccount.query.filter_by(
        provider=oauth_user["provider"],
        provider_user_id=oauth_user["provider_user_id"],
    ).first()

    if not exists:
        db.session.add(
            OAuthAccount(
                provider=oauth_user["provider"],
                provider_user_id=oauth_user["provider_user_id"],
                user_id=user.id,
            )
        )


@complete_profile_bp.route(
    "/complete_profile",
    methods=["GET", "POST"],
)
def complete_profile():
    oauth_user = session.get("oauth_user")

    if not oauth_user or not oauth_user.get("email"):
        return redirect("/auth/login")

    email = oauth_user["email"].strip().lower()

    existing_user = User.query.filter(db.func.lower(User.email) == email).first()

    if existing_user:
        _link_oauth_account(existing_user, oauth_user)
        db.session.commit()
        login_user(existing_user, remember=True)
        session.pop("oauth_user", None)
        return redirect("/profile")

    if request.method == "POST":
        try:
            age = int(request.form.get("age"))
            height = float(request.form.get("height"))
            weight = float(request.form.get("weight"))
            workouts = int(request.form.get("workouts"))
        except (TypeError, ValueError):
            flash("Заповніть вік, зріст, вагу та кількість тренувань.", "error")
            return render_template("auth/complete_profile.html", oauth_user=oauth_user)

        gender = request.form.get("gender") or None
        activity = request.form.get("activity") or None
        goal = request.form.get("goal") or None
        experience = request.form.get("experience") or None

        user = User(
            username=(oauth_user.get("username") or email.split("@")[0])[:50],
            email=email,
            password="oauth",
            is_premium=False,
        )

        db.session.add(user)
        db.session.flush()

        _link_oauth_account(user, oauth_user)

        profile = UserProfile(
            user_id=user.id,
            training_location="home",
            age=age,
            height=height,
            weight=weight,
            gender=gender,
            activity=activity,
            goal=goal,
            experience=experience,
            workouts_per_week=workouts,
            onboarding_completed=True,
        )

        db.session.add(profile)
        db.session.commit()

        login_user(user, remember=True)

        session.pop("oauth_user", None)

        return redirect("/profile")

    return render_template(
        "auth/complete_profile.html",
        oauth_user=oauth_user,
    )
