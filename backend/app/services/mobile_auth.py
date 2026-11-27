"""Sign-in of the mobile apps: email + password once, then a bearer token.

See backend/app/models/mobile_token.py for when a token stops working.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from backend.app.extensions import db
from backend.app.models.mobile_token import MobileToken
from backend.app.models.user import User
from backend.app.models.user_profile import UserProfile
from backend.app.utils.session_auth import fingerprint_matches, session_fingerprint

PLATFORMS = ("android", "ios")
TOKEN_LIFETIME = timedelta(days=90)
# last_used_at is informational: one write per token per hour is enough.
LAST_USED_RESOLUTION = timedelta(hours=1)
# Prefix makes a leaked token easy to recognise (and to scan for).
TOKEN_PREFIX = "nfm_"
MAX_DEVICE_NAME = 64
# A user rarely has more devices; older sign-ins are dropped beyond this.
MAX_TOKENS_PER_USER = 10


def _utcnow():
    return datetime.now(timezone.utc)


def _aware(value):
    return value if value is None or value.tzinfo else value.replace(tzinfo=timezone.utc)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def clean_device_name(value) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = "".join(ch for ch in value if ch.isprintable()).strip()
    return cleaned[:MAX_DEVICE_NAME] or None


def find_user_by_password(email: str, password: str):
    """The user for these credentials, or None (no hint which part was wrong)."""
    user = User.query.filter(db.func.lower(User.email) == email).first()
    if user is None or not user.check_password(password):
        return None
    return user


def ensure_profile(user) -> None:
    """Same as signing in on the website: older accounts may lack a profile."""
    if user.profile is None:
        db.session.add(UserProfile(user_id=user.id, training_location="home", onboarding_completed=False))
        db.session.commit()


def issue_token(user, platform: str, device_name: str | None):
    """Return ``(token, row)``. The token is shown to the app once."""
    token = TOKEN_PREFIX + secrets.token_urlsafe(32)
    now = _utcnow()
    row = MobileToken(
        user_id=user.id,
        token_hash=hash_token(token),
        fingerprint=session_fingerprint(user.id, user.password),
        platform=platform,
        device_name=device_name,
        created_at=now,
        last_used_at=now,
        expires_at=now + TOKEN_LIFETIME,
    )
    db.session.add(row)
    db.session.flush()

    stale = (
        MobileToken.query.filter_by(user_id=user.id)
        .order_by(MobileToken.created_at.desc(), MobileToken.id.desc())
        .offset(MAX_TOKENS_PER_USER)
        .all()
    )
    for old in stale:
        db.session.delete(old)
    db.session.commit()
    return token, row


def _row_for(token: str):
    if not isinstance(token, str) or not token.startswith(TOKEN_PREFIX) or len(token) > 128:
        return None
    return MobileToken.query.filter_by(token_hash=hash_token(token)).first()


def user_for_token(token: str):
    """The user a valid token belongs to, or None. Removes dead tokens."""
    row = _row_for(token)
    if row is None:
        return None
    now = _utcnow()
    user = row.user
    expired = _aware(row.expires_at) <= now
    if user is None or expired or not fingerprint_matches(user, row.fingerprint):
        db.session.delete(row)
        db.session.commit()
        return None
    last_used = _aware(row.last_used_at)
    if last_used is None or now - last_used >= LAST_USED_RESOLUTION:
        row.last_used_at = now
        db.session.commit()
    return user


def revoke_token(token: str) -> bool:
    row = _row_for(token)
    if row is None:
        return False
    db.session.delete(row)
    db.session.commit()
    return True


def expires_at_of(row) -> str:
    return _aware(row.expires_at).isoformat()
