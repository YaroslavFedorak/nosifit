from flask import Blueprint, render_template, request, redirect, session, flash

from backend.app.extensions import db
from backend.app.models.user import OAUTH_PASSWORD_MARKER, User
from backend.app.models.oauth_account import OAuthAccount
from backend.app.models.user_profile import UserProfile
from backend.app.utils.validation import (
    ValidationError,
    clean_choice,
    clean_username,
    parse_profile_number,
)
from web.app.routes.auth.main import start_user_session

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
        start_user_session(existing_user)
        return redirect("/profile")

    if request.method == "POST":
        try:
            age = parse_profile_number("age", request.form.get("age"), required=True)
            height = parse_profile_number("height", request.form.get("height"), required=True)
            weight = parse_profile_number("weight", request.form.get("weight"), required=True)
            workouts = parse_profile_number(
                "workouts_per_week", request.form.get("workouts"), required=True
            )
            gender = clean_choice("gender", request.form.get("gender"))
            activity = clean_choice("activity", request.form.get("activity"))
            goal = clean_choice("goal", request.form.get("goal"))
            experience = clean_choice("experience", request.form.get("experience"))
        except ValidationError:
            flash("Заповніть вік, зріст, вагу та кількість тренувань.", "error")
            return render_template("auth/complete_profile.html", oauth_user=oauth_user)

        user = User(
            username=clean_username(oauth_user.get("username"))
            or email.split("@")[0][:50],
            email=email,
            password=OAUTH_PASSWORD_MARKER,
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

        start_user_session(user)

        return redirect("/profile")

    return render_template(
        "auth/complete_profile.html",
        oauth_user=oauth_user,
    )
