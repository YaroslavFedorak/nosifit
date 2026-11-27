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

    session[key] = {
        "hash": hash_code(code),
        "issued": int(time.time()),
        # Wrong attempts are counted per issued code (verify_session_code).
        "attempt_id": secrets.token_hex(16),
        **extra,
    }


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

    Wrong attempts are counted on the server, per issued code (the entry's
    random ``attempt_id``). The session cookie is client-side: whoever holds
    it can send the copy that still contains the code again and again. So
    the count is never reset when the limit is hit (a reset would give every
    replay MAX_CODE_ATTEMPTS new guesses); it ends with its window, and a
    newly issued code gets a new id and so a fresh count.
    """
    from flask import session

    from backend.app.utils.rate_limit import hit_limit, reset_limit

    entry = load_session_code(key)
    if entry is None:
        return "expired"

    scope = f"code-{key}"
    # Entries issued before attempt ids existed share one count per user.
    counter = f"{user_id}:{entry.get('attempt_id') or 'legacy'}"
    if hit_limit(scope, counter, MAX_CODE_ATTEMPTS, CODE_TTL_SECONDS):
        session.pop(key, None)
        return "expired"

    if given is None or not check_code(entry.get("hash"), given):
        return "wrong"

    reset_limit(scope, counter)
    return "ok"
