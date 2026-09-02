from flask import Blueprint, redirect, url_for, session, jsonify
from flask_login import login_user
from web.app.models.user import User
from web.app.models.oauth_account import OAuthAccount
from web.app.models.user_profile import UserProfile
from web.app import db, oauth

google_bp = Blueprint("google_oauth", __name__)


@google_bp.route("/auth/google")
def google_login():
    google = oauth.create_client("google")
    redirect_uri = url_for("google_oauth.google_callback", _external=True)
    return google.authorize_redirect(redirect_uri)


@google_bp.route("/auth/google/callback")
def google_callback():
    google = oauth.create_client("google")

    try:
        token = google.authorize_access_token()
    except Exception:
        return jsonify({"error": "Google token error"}), 400

    userinfo_endpoint = google.server_metadata["userinfo_endpoint"]
    user_info = google.get(userinfo_endpoint).json()

    if "sub" not in user_info:
        return jsonify({"error": "Google user error"}), 400

    google_id = user_info["sub"]
    email = user_info.get("email")
    name = user_info.get("name")

    oauth_acc = OAuthAccount.query.filter_by(
        provider="google", provider_user_id=google_id
    ).first()

    if oauth_acc:
        user = oauth_acc.user

        if not user.profile:
            profile = UserProfile(
                user_id=user.id, training_location="home", onboarding_completed=False
            )
            db.session.add(profile)
            db.session.commit()

        login_user(user)
        return redirect("/profile")

    if email:
        user = User.query.filter_by(email=email).first()
        if user:

            if not user.profile:
                profile = UserProfile(
                    user_id=user.id,
                    training_location="home",
                    onboarding_completed=False,
                )
                db.session.add(profile)

            db.session.add(
                OAuthAccount(
                    provider="google", provider_user_id=google_id, user_id=user.id
                )
            )
            db.session.commit()

            login_user(user)
            return redirect("/profile")

    session["oauth_user"] = {
        "provider": "google",
        "provider_user_id": google_id,
        "email": email,
        "name": name,
    }

    return redirect("/auth/complete_profile")
