"""Sign-in of the NosiFit mobile apps (Android, iOS).

POST /api/v1/mobile/auth/login trades email and password for a bearer
token. The app then calls the ordinary API with
``Authorization: Bearer <token>`` (auth/mobile_token.py).

The login shares its rate-limit counters with the website's sign-in form,
so switching between the two gives no extra guesses.
"""

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from auth.mobile_token import bearer_token
from backend.app.services import mobile_auth
from backend.app.services.consent import has_current_consent
from backend.app.utils.client_ip import client_ip
from backend.app.utils.rate_limit import hit_limit, reset_limit
from backend.app.utils.validation import normalize_email

mobile_auth_api = Blueprint("mobile_auth_api", __name__, url_prefix="/api/mobile/auth")

# Same buckets and numbers as /auth/login (web/app/routes/auth/main.py).
LOGIN_LIMIT_PER_EMAIL = (10, 15 * 60)
LOGIN_LIMIT_PER_IP = (50, 5 * 60)
MAX_PASSWORD_LENGTH = 1024


def _error(code: str, message: str, status: int):
    response = jsonify({"error": message, "code": code, "message": message})
    response.status_code = status
    return response


def _account(user):
    return {
        "user": {"id": user.id, "name": user.username, "email": user.email},
        "consent_required": not has_current_consent(user),
        "features": {"plan_generation": bool(user.is_premium)},
    }


@mobile_auth_api.post("/login")
def login():
    """Sign in with email and password; answers with a bearer token."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _error("invalid_input", "A JSON object is required", 400)

    email = normalize_email(data.get("email")) if isinstance(data.get("email"), str) else ""
    password = data.get("password")
    platform = data.get("platform")
    if not email or not isinstance(password, str) or not password or len(password) > MAX_PASSWORD_LENGTH:
        return _error("invalid_input", "email and password are required", 400)
    if platform not in mobile_auth.PLATFORMS:
        return _error("invalid_input", "platform must be android or ios", 400)

    if hit_limit("login-ip", client_ip(), *LOGIN_LIMIT_PER_IP) or hit_limit(
        "login-email", email, *LOGIN_LIMIT_PER_EMAIL
    ):
        return _error("rate_limited", "Too many sign-in attempts. Try again later.", 429)

    # One answer for "no such user" and "wrong password".
    user = mobile_auth.find_user_by_password(email, password)
    if user is None:
        return _error("invalid_credentials", "Wrong email or password", 401)

    reset_limit("login-email", email)
    mobile_auth.ensure_profile(user)
    token, row = mobile_auth.issue_token(user, platform, mobile_auth.clean_device_name(data.get("device_name")))
    return jsonify(
        {
            "token": token,
            "token_type": "Bearer",
            "expires_at": mobile_auth.expires_at_of(row),
            **_account(user),
        }
    )


@mobile_auth_api.get("/session")
@login_required
def session_info():
    """Who the token belongs to and whether consent is still needed."""
    return jsonify(_account(current_user))


@mobile_auth_api.post("/logout")
@login_required
def logout():
    """Revoke the bearer token of this request."""
    token = bearer_token(request)
    if token is not None:
        mobile_auth.revoke_token(token)
    return jsonify({"status": "ok"})
