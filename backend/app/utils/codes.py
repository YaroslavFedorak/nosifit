"""One-time email codes kept in the Flask session.

The Flask session cookie is signed but NOT encrypted: anyone can base64-decode
it. So the session must never hold the code itself, only an HMAC of it.
"""

import hashlib
import hmac
import secrets

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
