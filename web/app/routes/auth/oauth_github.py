from flask import Blueprint, redirect, request, session, current_app, jsonify
import requests
from flask_login import login_user
from web.app.models.user import User
from web.app.models.oauth_account import OAuthAccount
from web.app.models.user_profile import UserProfile
from web.app import db

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

    client_id = current_app.config["GITHUB_CLIENT_ID"]
    client_secret = current_app.config["GITHUB_CLIENT_SECRET"]

    token_res = requests.post(
        "https://github.com/login/oauth/access_token",
        headers={"Accept": "application/json"},
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
        },
    ).json()

    if "access_token" not in token_res:
        return jsonify({"error": "GitHub token error"}), 400

    access_token = token_res["access_token"]

    user_res = requests.get(
        "https://api.github.com/user",
        headers={"Authorization": f"Bearer {access_token}"},
    ).json()

    if "id" not in user_res:
        return jsonify({"error": "GitHub user error"}), 400

    github_id = str(user_res["id"])
    username = user_res.get("login")

    email_res = requests.get(
        "https://api.github.com/user/emails",
        headers={"Authorization": f"Bearer {access_token}"},
    ).json()

    if not isinstance(email_res, list):
        return jsonify({"error": "GitHub email error"}), 400

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
