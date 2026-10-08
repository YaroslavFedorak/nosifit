from flask import Blueprint, redirect, request, session, current_app, jsonify
import requests
import logging
import secrets
from urllib.parse import urlencode
from web.app.routes.auth.main import start_user_session
from web.app.routes.auth.telegram_session import pending_link_redirect
from backend.app.models.user import User
from backend.app.models.oauth_account import OAuthAccount
from backend.app.models.user_profile import UserProfile
from backend.app.extensions import db

logger = logging.getLogger(__name__)

github_bp = Blueprint("github", __name__)


@github_bp.route("/auth/github")
def github_login():
    client_id = current_app.config.get("GITHUB_CLIENT_ID")
    if not client_id:
        return jsonify({"error": "GitHub OAuth not configured"}), 400

    # Ties the callback to this browser: without it an attacker can feed a
    # victim their own ?code= and log the victim into the attacker's account.
    state = secrets.token_urlsafe(32)
    session["github_oauth_state"] = state

    query = urlencode({"client_id": client_id, "scope": "user:email", "state": state})
    return redirect(f"https://github.com/login/oauth/authorize?{query}")


def _oauth_failed(message, status=400):
    return jsonify({"error": message}), status


@github_bp.route("/auth/github/callback")
def github_callback():
    expected_state = session.pop("github_oauth_state", None)
    state = request.args.get("state") or ""
    if not expected_state or not secrets.compare_digest(expected_state, state):
        return redirect("/auth/login")

    code = request.args.get("code")
    if not code:
        # User pressed "Cancel" on GitHub, or opened the callback directly
        return redirect("/auth/login")

    client_id = current_app.config.get("GITHUB_CLIENT_ID")
    client_secret = current_app.config.get("GITHUB_CLIENT_SECRET")

    if not client_id or not client_secret:
        return jsonify({"error": "GitHub OAuth not configured"}), 500

    try:
        token_res = requests.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
            },
            timeout=10,
        ).json()
    except Exception:
        logger.exception("GitHub token request failed")
        return _oauth_failed("GitHub sign-in failed", 502)

    if not isinstance(token_res, dict) or "access_token" not in token_res:
        logger.warning("GitHub token error: %s", (token_res or {}).get("error") if isinstance(token_res, dict) else None)
        return _oauth_failed("GitHub sign-in failed")

    access_token = token_res["access_token"]

    try:
        user_res = requests.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        ).json()
    except Exception:
        logger.exception("GitHub user request failed")
        return _oauth_failed("GitHub sign-in failed", 502)

    if not isinstance(user_res, dict) or "id" not in user_res:
        return _oauth_failed("GitHub sign-in failed")

    github_id = str(user_res["id"])
    username = user_res.get("login")

    try:
        email_res = requests.get(
            "https://api.github.com/user/emails",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        ).json()
    except Exception:
        logger.exception("GitHub email request failed")
        return _oauth_failed("GitHub sign-in failed", 502)

    # Only a verified address may be linked to an existing account.
    email = None
    if isinstance(email_res, list):
        verified = [e for e in email_res if isinstance(e, dict) and e.get("verified")]
        primary = next((e for e in verified if e.get("primary")), None)
        chosen = primary or (verified[0] if verified else None)
        if chosen and chosen.get("email"):
            email = chosen["email"].strip().lower()
    else:
        # Private email or missing user:email scope: GitHub returns {"message": ...}
        error_msg = email_res.get("message", "") if isinstance(email_res, dict) else ""
        logger.warning("GitHub email API error for user %s: %s", github_id, error_msg)

    oauth_acc = OAuthAccount.query.filter_by(
        provider="github", provider_user_id=github_id
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
                    provider="github", provider_user_id=github_id, user_id=user.id
                )
            )
            db.session.commit()
            start_user_session(user)
            return redirect(pending_link_redirect("/profile"))

    # No usable email: GitHub's own noreply address is unique per account.
    noreply_email = f"{github_id}+{username or 'user'}@users.noreply.github.com".lower()

    session["oauth_user"] = {
        "provider": "github",
        "provider_user_id": github_id,
        "username": username or f"github_{github_id}",
        "email": email or noreply_email,
    }

    return redirect("/auth/complete_profile")
