"""Session state related to Telegram sign-in.

Telegram sessions
    The bot signs a user in with POST /api/telegram/login and then uses the
    ordinary Flask-Login session cookie, exactly like a browser. Such a
    session is marked with the TelegramIdentity it was created from and:
    - dies as soon as that identity is disconnected (checked per request);
    - gets no "remember me" cookie (it could restore an unmarked session);
    - may only call the API the bot needs. Changing email or password,
      deleting the account and (dis)connecting sign-in methods stay with
      browser sessions, so a lost Telegram account exposes nutrition data,
      not control over the NosiFit account.

Pending link
    /auth/telegram/link/<token> keeps the token's hash in the session while
    the user signs in. Login replaces the session, so start_user_session
    carries this one entry over (with a fresh CSRF value).

Recent sign-in
    Connecting Telegram grants lasting access (it survives a password
    change), so a stolen or long-lived session must not be enough: the
    confirmation needs a sign-in (password, Google or GitHub) from the last
    RECENT_AUTH_SECONDS. Sessions restored from a "remember me" cookie have
    no sign-in time and count as old.
"""

import secrets
import time

from flask import jsonify, request, session, url_for
from flask_login import current_user, login_user, logout_user

TELEGRAM_SESSION_KEY = "tg_identity"
PENDING_LINK_KEY = "tg_link"
AUTH_AT_KEY = "auth_at"
RECENT_AUTH_SECONDS = 15 * 60

# Paths a Telegram session may use (everything the bot calls). The
# /api/telegram/ endpoints check the bot's signature, not the session.
TELEGRAM_SESSION_PREFIXES = ("/api/nutrition/", "/api/telegram/")
TELEGRAM_SESSION_PATHS = frozenset({"/auth/logout"})


def start_telegram_session(user, identity) -> None:
    session.clear()
    login_user(user, remember=False)
    session[TELEGRAM_SESSION_KEY] = identity.id


def is_telegram_session() -> bool:
    return TELEGRAM_SESSION_KEY in session


def enforce_telegram_session():
    """before_request: scope and revocation of Telegram sessions."""
    identity_id = session.get(TELEGRAM_SESSION_KEY)
    if identity_id is None:
        return None

    path = request.path
    if not (path.startswith(TELEGRAM_SESSION_PREFIXES) or path in TELEGRAM_SESSION_PATHS):
        response = jsonify(
            {"error": "Not available in a Telegram session", "code": "telegram_session_scope"}
        )
        response.status_code = 403
        return response

    from backend.app.extensions import db
    from backend.app.models.telegram import TelegramIdentity

    identity = None
    if isinstance(identity_id, int) and not isinstance(identity_id, bool):
        identity = db.session.get(TelegramIdentity, identity_id)

    if (
        identity is None
        or not current_user.is_authenticated
        or identity.user_id != current_user.id
    ):
        logout_user()
        session.clear()
        response = jsonify({"error": "Session expired", "code": "session_revoked"})
        response.status_code = 401
        return response
    return None


# --- Recent sign-in ----------------------------------------------------------------


def mark_authenticated_now() -> None:
    session[AUTH_AT_KEY] = int(time.time())


def is_recently_authenticated() -> bool:
    auth_at = session.get(AUTH_AT_KEY)
    if not isinstance(auth_at, int) or isinstance(auth_at, bool):
        return False
    return 0 <= time.time() - auth_at <= RECENT_AUTH_SECONDS


# --- Pending link ------------------------------------------------------------------


def set_pending_link(token_hash: str, expires_at: float) -> None:
    session[PENDING_LINK_KEY] = {
        "h": token_hash,
        "csrf": secrets.token_urlsafe(32),
        "exp": int(expires_at),
    }


def get_pending_link():
    entry = session.get(PENDING_LINK_KEY)
    if (
        not isinstance(entry, dict)
        or not isinstance(entry.get("h"), str)
        or not isinstance(entry.get("csrf"), str)
        or not isinstance(entry.get("exp"), int)
        or entry["exp"] < time.time()
    ):
        session.pop(PENDING_LINK_KEY, None)
        return None
    return entry


def clear_pending_link() -> None:
    session.pop(PENDING_LINK_KEY, None)


def carry_pending_link_over(previous) -> None:
    """Put a still-valid pending link back after session.clear()."""
    if not isinstance(previous, dict):
        return
    session[PENDING_LINK_KEY] = previous
    entry = get_pending_link()
    if entry is not None:
        # New session, new form token.
        entry["csrf"] = secrets.token_urlsafe(32)
        session[PENDING_LINK_KEY] = entry


def pending_link_redirect(default: str) -> str:
    """Where to go after signing in: the pending Telegram link, if any."""
    if get_pending_link() is not None:
        return url_for("telegram_link.link_page")
    return default
