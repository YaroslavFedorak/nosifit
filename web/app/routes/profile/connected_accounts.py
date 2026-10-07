"""Disconnecting Telegram from the profile page.

A browser session alone is not enough: the user re-authenticates with the
current password or, for accounts without one, a code sent to the account
email. This stops a stolen session or a forged request from removing the
owner's Telegram (and the bot sessions with it). An account never loses its
last way to sign in.
"""

from flask import Blueprint, current_app, jsonify, request, session
from flask_login import current_user, login_required

from backend.app.services import telegram_auth as tg
from backend.app.utils.codes import new_code, store_session_code, verify_session_code
from backend.app.utils.mailer import EmailSendError, send_email_code
from web.app.security import hit_limit, too_many_requests

connected_accounts_bp = Blueprint("connected_accounts", __name__)

SESSION_KEY = "tg_unlink_code"
SEND_LIMIT_PER_USER = (5, 60 * 60)
ATTEMPT_LIMIT_PER_USER = (10, 15 * 60)


def connected_accounts_context(user) -> dict:
    """What the profile page shows; computed on the server only."""
    methods = tg.sign_in_methods(user)
    identity = tg.identity_for_user(user.id)
    bot = tg.clean_bot_username(current_app.config.get("TELEGRAM_BOT_USERNAME"))
    return {
        "has_password": methods["password"],
        "google": methods["google"],
        "github": methods["github"],
        "telegram": identity is not None,
        "telegram_username": identity.telegram_username if identity else None,
        # "connect" makes the bot start the linking flow right away.
        "telegram_connect_url": f"https://t.me/{bot}?start=connect" if bot else None,
        "method_count": sum(1 for enabled in methods.values() if enabled),
    }


def _payload() -> dict:
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else request.form.to_dict()


def _error(message: str, status: int = 400):
    return jsonify({"status": "error", "message": message}), status


@connected_accounts_bp.post("/profile/telegram/disconnect/request")
@login_required
def request_code():
    if tg.identity_for_user(current_user.id) is None:
        return _error("not_connected", 404)
    if current_user.has_password:
        return _error("password_required")

    if hit_limit("tg-unlink-send", current_user.id, *SEND_LIMIT_PER_USER):
        return too_many_requests()

    code = new_code()
    try:
        send_email_code(current_user.email, code)
    except EmailSendError:
        return _error("send_failed", 503)

    store_session_code(SESSION_KEY, code, user_id=current_user.id)
    return jsonify({"status": "sent"})


def _reauthenticated(data) -> str | None:
    """None when the user proved it is them, else an error message."""
    if current_user.has_password:
        if hit_limit("tg-unlink-password", current_user.id, *ATTEMPT_LIMIT_PER_USER):
            return "rate_limited"
        password = data.get("password")
        if not isinstance(password, str) or not current_user.check_password(password):
            return "wrong_password"
        return None

    entry = session.get(SESSION_KEY)
    if not isinstance(entry, dict) or entry.get("user_id") != current_user.id:
        session.pop(SESSION_KEY, None)
        return "expired"
    result = verify_session_code(SESSION_KEY, data.get("code"), current_user.id)
    if result == "ok":
        session.pop(SESSION_KEY, None)
        return None
    return "expired" if result == "expired" else "wrong_code"


@connected_accounts_bp.post("/profile/telegram/disconnect")
@login_required
def disconnect_telegram():
    if tg.identity_for_user(current_user.id) is None:
        return _error("not_connected", 404)

    # Checked before asking for a password, so the user learns early.
    if tg.remaining_methods_without(current_user, "telegram") == 0:
        return _error("last_method")

    problem = _reauthenticated(_payload())
    if problem == "rate_limited":
        return too_many_requests()
    if problem:
        return _error(problem)

    user = current_user._get_current_object()
    result = tg.unlink_telegram(user)
    if result == "not_connected":
        return _error("not_connected", 404)
    if result == "last_method":
        return _error("last_method")

    tg.notify_telegram_unlinked(user)
    return jsonify({"status": "disconnected"})
