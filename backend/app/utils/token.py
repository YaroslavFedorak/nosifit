"""Password reset links.

The token carries the user id and a fingerprint of the current password hash.
Setting a new password changes the hash, so a link works only once and every
older link dies with it.
"""

import hmac

from flask import current_app
from itsdangerous import BadData, URLSafeTimedSerializer

from backend.app.extensions import db
from backend.app.utils.session_auth import session_fingerprint

RESET_TOKEN_MAX_AGE = 3600
_SALT = "password-reset-v2"


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=_SALT)


def generate_reset_token(user):
    return _serializer().dumps(
        {"uid": user.id, "fp": session_fingerprint(user.id, user.password)}
    )


def verify_reset_token(token, max_age=RESET_TOKEN_MAX_AGE):
    """Return the user the token was issued for, or None."""
    from backend.app.models.user import User

    try:
        data = _serializer().loads(token, max_age=max_age)
    except (BadData, TypeError, ValueError):
        return None

    if not isinstance(data, dict) or not isinstance(data.get("uid"), int):
        return None

    user = db.session.get(User, data["uid"])
    if user is None:
        return None

    expected = session_fingerprint(user.id, user.password)
    if not hmac.compare_digest(expected, str(data.get("fp", ""))):
        return None
    return user
