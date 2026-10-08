"""Binds login sessions to the user's current password hash.

Flask-Login stores ``User.get_id()`` in the session and in the "remember me"
cookie. Adding a fingerprint of the password hash there means a password
change or reset invalidates every other session and remember cookie, which
plain integer ids never do.
"""

import hashlib
import hmac

from flask import current_app


def session_fingerprint(user_id, password_hash) -> str:
    key = (current_app.config.get("SECRET_KEY") or "").encode()
    msg = f"{user_id}:{password_hash}".encode()
    return hmac.new(key, msg, hashlib.sha256).hexdigest()[:32]


def make_session_id(user) -> str:
    return f"{user.id}:{session_fingerprint(user.id, user.password)}"


def parse_session_id(value):
    """Return ``(user_id, fingerprint)`` or ``None`` for malformed ids."""
    user_id, sep, fingerprint = str(value or "").partition(":")
    if not sep or not user_id.isdigit() or not fingerprint:
        return None
    return int(user_id), fingerprint


def fingerprint_matches(user, fingerprint) -> bool:
    expected = session_fingerprint(user.id, user.password)
    return hmac.compare_digest(expected, str(fingerprint))
