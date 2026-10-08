import logging

from flask import Blueprint, redirect, url_for, session, jsonify
from backend.app.models.user import User
from backend.app.models.oauth_account import OAuthAccount
from backend.app.models.user_profile import UserProfile
from backend.app.extensions import db, oauth
from web.app.routes.auth.main import start_user_session
from web.app.routes.auth.telegram_session import pending_link_redirect

logger = logging.getLogger(__name__)

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
        logger.warning("Google token exchange failed", exc_info=True)
        return jsonify({"error": "Google token error"}), 400

    user_info = token.get("userinfo") if isinstance(token, dict) else None
    if not user_info:
        userinfo_endpoint = google.server_metadata["userinfo_endpoint"]
        user_info = google.get(userinfo_endpoint).json()

    if not isinstance(user_info, dict) or "sub" not in user_info:
        return jsonify({"error": "Google user error"}), 400

    google_id = str(user_info["sub"])
    # Only an address Google has verified may be matched to (and thereby log
    # into) an existing NosiFit account.
    email = None
    if user_info.get("email_verified") is True:
        email = (user_info.get("email") or "").strip().lower() or None
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

        start_user_session(user)
        return redirect(pending_link_redirect("/profile"))

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

            start_user_session(user)
            return redirect(pending_link_redirect("/profile"))

    if not email:
        return redirect("/auth/login")

    session["oauth_user"] = {
        "provider": "google",
        "provider_user_id": google_id,
        "email": email,
        "username": name,
    }

    return redirect("/auth/complete_profile")
