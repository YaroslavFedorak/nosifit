from flask import Blueprint, redirect, request, session, current_app, jsonify
import requests
from flask_login import login_user
from backend.app.models.user import User
from backend.app.models.oauth_account import OAuthAccount
from backend.app.models.user_profile import UserProfile
from backend.app.extensions import db

github_bp = Blueprint("github", __name__)


@github_bp.route("/auth/github")
def github_login():
    client_id = current_app.config.get("GITHUB_CLIENT_ID")
    if not client_id:
        return jsonify({"error": "GitHub OAuth not configured"}), 400

    github_auth_url = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={client_id}&scope=user:email"
    )

    return redirect(github_auth_url)


@github_bp.route("/auth/github/callback")
def github_callback():
    code = request.args.get("code")

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
    except Exception as e:
        return jsonify({"error": f"GitHub token request failed: {str(e)}"}), 500

    if "access_token" not in token_res:
        error_msg = token_res.get("error_description", token_res.get("error", "Unknown error"))
        return jsonify({"error": f"GitHub token error: {error_msg}"}), 400

    access_token = token_res["access_token"]

    try:
        user_res = requests.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        ).json()
    except Exception as e:
        return jsonify({"error": f"GitHub user request failed: {str(e)}"}), 500

    if "id" not in user_res:
        error_msg = user_res.get("message", "Unknown error")
        return jsonify({"error": f"GitHub user error: {error_msg}"}), 400

    github_id = str(user_res["id"])
    username = user_res.get("login")

    try:
        email_res = requests.get(
            "https://api.github.com/user/emails",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        ).json()
    except Exception as e:
        return jsonify({"error": f"GitHub email request failed: {str(e)}"}), 500

    if not isinstance(email_res, list):
        return jsonify({"error": f"GitHub email error: expected list, got {type(email_res).__name__}"}), 400

    primary_email = None
    for e in email_res:
        if e.get("primary"):
            primary_email = e.get("email")

    email = primary_email

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
                    provider="github", provider_user_id=github_id, user_id=user.id
                )
            )
            db.session.commit()
            login_user(user)
            return redirect("/profile")

    session["oauth_user"] = {
        "provider": "github",
        "provider_user_id": github_id,
        "username": username,
        "email": email,
    }

    return redirect("/auth/complete_profile")
