"""Request signatures between the Telegram bot and the web app.

The bot vouches for a Telegram user id (taken from the Telegram update
itself). The web app believes it only when the request carries an HMAC made
with TELEGRAM_BOT_API_SECRET, which only the two services know. The secret
never travels: each request carries a signature over a timestamp, a random
nonce, the method, the path and the body. The server rejects stale
timestamps and reused nonces, so a captured request cannot be replayed.

Pure Python on purpose: the bot imports it without Flask.
"""

import hashlib
import hmac
import secrets
import time

VERSION = "v1"
HEADER_TIMESTAMP = "X-NosiFit-Bot-Timestamp"
HEADER_NONCE = "X-NosiFit-Bot-Nonce"
HEADER_SIGNATURE = "X-NosiFit-Bot-Signature"

# Clock skew tolerated between the two services.
MAX_SKEW_SECONDS = 60
MIN_SECRET_LENGTH = 32


def _canonical(timestamp: str, nonce: str, method: str, path: str, body: bytes) -> bytes:
    body_hash = hashlib.sha256(body or b"").hexdigest()
    return "\n".join(
        (VERSION, timestamp, nonce, method.upper(), path, body_hash)
    ).encode()


def compute_signature(
    secret: str, timestamp: str, nonce: str, method: str, path: str, body: bytes
) -> str:
    return hmac.new(
        secret.encode(), _canonical(timestamp, nonce, method, path, body), hashlib.sha256
    ).hexdigest()


def sign_request(secret: str, method: str, path: str, body: bytes) -> dict:
    """Headers for one request from the bot."""
    timestamp = str(int(time.time()))
    nonce = secrets.token_urlsafe(18)
    return {
        HEADER_TIMESTAMP: timestamp,
        HEADER_NONCE: nonce,
        HEADER_SIGNATURE: compute_signature(secret, timestamp, nonce, method, path, body),
    }


def check_signature(
    secret: str | None,
    headers,
    method: str,
    path: str,
    body: bytes,
    now: float | None = None,
) -> str | None:
    """The request's nonce when the signature is valid and fresh, else None.

    The caller must still make sure the nonce has not been seen before.
    """
    if not secret or len(secret) < MIN_SECRET_LENGTH:
        return None

    timestamp = headers.get(HEADER_TIMESTAMP) or ""
    nonce = headers.get(HEADER_NONCE) or ""
    signature = headers.get(HEADER_SIGNATURE) or ""

    if not (timestamp.isdigit() and len(timestamp) <= 12):
        return None
    if not (16 <= len(nonce) <= 64) or not all(
        c.isalnum() or c in "-_" for c in nonce
    ):
        return None
    if len(signature) != 64:
        return None

    current = time.time() if now is None else now
    if abs(current - int(timestamp)) > MAX_SKEW_SECONDS:
        return None

    expected = compute_signature(secret, timestamp, nonce, method, path, body)
    if not hmac.compare_digest(expected, signature):
        return None
    return nonce
