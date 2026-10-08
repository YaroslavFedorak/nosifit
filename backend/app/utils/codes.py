"""One-time email codes kept in the Flask session.

The Flask session cookie is signed but NOT encrypted: anyone can base64-decode
it. So the session must never hold the code itself, only an HMAC of it.
"""

import hashlib
import hmac
import secrets
import time

from flask import current_app


def new_code() -> str:
    return f"{secrets.randbelow(900000) + 100000}"


def hash_code(code) -> str:
    key = (current_app.config.get("SECRET_KEY") or "").encode()
    return hmac.new(key, str(code).strip().encode(), hashlib.sha256).hexdigest()


def check_code(stored_hash, given) -> bool:
    if not stored_hash or given is None:
        return False
    return hmac.compare_digest(str(stored_hash), hash_code(given))


# --- Codes kept in the session ------------------------------------------------

CODE_TTL_SECONDS = 10 * 60
MAX_CODE_ATTEMPTS = 5


def store_session_code(key: str, code: str, **extra) -> None:
    from flask import session

    session[key] = {"hash": hash_code(code), "issued": int(time.time()), **extra}


def load_session_code(key: str):
    """The stored entry, or None when missing or older than CODE_TTL_SECONDS."""
    from flask import session

    entry = session.get(key)
    if not isinstance(entry, dict):
        session.pop(key, None)
        return None
    if time.time() - int(entry.get("issued", 0)) > CODE_TTL_SECONDS:
        session.pop(key, None)
        return None
    return entry


def verify_session_code(key: str, given, user_id) -> str:
    """Check a code typed by ``user_id``: "ok", "expired" or "wrong".

    Wrong attempts are counted on the server; the session cookie is
    client-side and could be replayed to reset a counter kept inside it.
    After MAX_CODE_ATTEMPTS wrong attempts the code is discarded.
    """
    from flask import session

    from web.app.security import hit_limit, reset_limit

    entry = load_session_code(key)
    if entry is None:
        return "expired"

    scope = f"code-{key}"
    if hit_limit(scope, user_id, MAX_CODE_ATTEMPTS, CODE_TTL_SECONDS):
        session.pop(key, None)
        reset_limit(scope, user_id)
        return "expired"

    if given is None or not check_code(entry.get("hash"), given):
        return "wrong"

    reset_limit(scope, user_id)
    return "ok"
