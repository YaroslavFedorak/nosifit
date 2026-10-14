"""Telegram as a sign-in identity: validation, link tokens, linking rules.

Invariants (enforced here and by unique constraints in the database):
- the Telegram numeric user id is the identity; usernames are display only;
- one Telegram account belongs to at most one NosiFit user and one user has
  at most one Telegram account;
- a Telegram account is never attached to an existing user because of a
  matching email: only a signed-in user confirming a one-time link does it;
- an account always keeps at least one way to sign in.
"""

import hashlib
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlencode

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError

from backend.app.extensions import db
from backend.app.models.oauth_account import OAuthAccount
from backend.app.models.telegram import TelegramIdentity, TelegramLinkToken
from backend.app.models.user import OAUTH_PASSWORD_MARKER, User
from backend.app.models.user_profile import UserProfile
from backend.app.services.email_outbox import enqueue_notice
from backend.app.utils.mailer import send_email
from backend.app.utils.validation import clean_username

logger = logging.getLogger(__name__)

# Telegram user ids are positive and fit in 52 bits today; BIGINT is the
# hard limit of the column.
TELEGRAM_ID_MAX = 2**63 - 1
_USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{4,32}$")
# secrets.token_urlsafe(32) -> 43 URL-safe characters (256 bits).
LINK_TOKEN_BYTES = 32
_LINK_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{43}$")
NAME_MAX_LENGTH = 64

LINK_TTL_MIN = 60
LINK_TTL_MAX = 30 * 60

OAUTH_PROVIDERS = ("google", "github")

# ?via= on the link: the sign-in the user picked in the bot. Only these
# fixed endpoints can be targets, so the parameter is no open redirect.
LINK_SIGN_IN_METHODS = {
    "google": ("google_oauth.google_login", "GOOGLE_CLIENT_ID"),
    "github": ("github.github_login", "GITHUB_CLIENT_ID"),
    "password": ("telegram_link.link_page", None),
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


# --- Input validation -------------------------------------------------------------


def parse_telegram_user_id(value) -> int | None:
    """A positive Telegram user id, else None (bools, floats, junk, overflow)."""
    if isinstance(value, bool):
        return None
    if isinstance(value, str):
        value = value.strip()
        if not value.isdigit() or len(value) > 19:
            return None
        value = int(value)
    if isinstance(value, int) and 0 < value <= TELEGRAM_ID_MAX:
        return value
    return None


def clean_telegram_username(value) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip().lstrip("@")
    return value if _USERNAME_RE.match(value) else None


def clean_telegram_name(value) -> str | None:
    """Display name from Telegram: printable, single-spaced, bounded."""
    if not isinstance(value, str):
        return None
    printable = "".join(ch for ch in value if ch.isprintable())
    name = " ".join(printable.split())[:NAME_MAX_LENGTH]
    return name or None


def clean_bot_username(value) -> str | None:
    """Bot username for t.me links; anything else is ignored."""
    username = clean_telegram_username(value)
    return username if username and len(username) >= 5 else None


def is_link_token_format(token) -> bool:
    return isinstance(token, str) and bool(_LINK_TOKEN_RE.match(token))


def hash_link_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# The page that opens a link token: web.app.routes.auth.telegram_link
# (/auth/telegram/link/<token>). The bot API builds the link without the web
# app's URL map, so it works when the API runs on its own; a test keeps the
# two equal.
LINK_PAGE_PATH = "/auth/telegram/link/"


def link_page_path(token: str, via: str | None = None) -> str:
    path = LINK_PAGE_PATH + quote(token, safe="")
    if via:
        path += "?" + urlencode({"via": via})
    return path


def link_token_ttl(config) -> int:
    try:
        ttl = int(config.get("TELEGRAM_LINK_TOKEN_TTL", 600))
    except (TypeError, ValueError):
        ttl = 600
    return max(LINK_TTL_MIN, min(LINK_TTL_MAX, ttl))


# --- Lookups ------------------------------------------------------------------------


def identity_for_telegram(telegram_user_id: int) -> TelegramIdentity | None:
    return TelegramIdentity.query.filter_by(telegram_user_id=telegram_user_id).first()


def identity_for_user(user_id: int) -> TelegramIdentity | None:
    return TelegramIdentity.query.filter_by(user_id=user_id).first()


def lock_user(user_id: int) -> User | None:
    """Row lock on the user for the rest of the transaction.

    Serialises changes to the user's sign-in methods, so two concurrent
    "disconnect" requests cannot each see the other method and remove both.
    """
    return db.session.execute(
        select(User).where(User.id == user_id).with_for_update()
    ).scalar_one_or_none()


def sign_in_methods(user) -> dict:
    providers = {
        provider
        for (provider,) in db.session.query(OAuthAccount.provider)
        .filter(OAuthAccount.user_id == user.id)
        .all()
    }
    return {
        "password": bool(user.has_password),
        "google": "google" in providers,
        "github": "github" in providers,
        "telegram": identity_for_user(user.id) is not None,
    }


def remaining_methods_without(user, method: str) -> int:
    """How many ways to sign in stay after removing ``method``."""
    methods = sign_in_methods(user)
    methods[method] = False
    return sum(1 for enabled in methods.values() if enabled)


# --- Link tokens --------------------------------------------------------------------


def issue_link_token(
    telegram_user_id: int,
    *,
    username: str | None,
    name: str | None,
    ttl_seconds: int,
) -> str:
    """New one-time token for ``telegram_user_id``; older ones stop working."""
    now = utcnow()

    # Housekeeping: expired tokens are useless; keep the table small.
    db.session.execute(delete(TelegramLinkToken).where(TelegramLinkToken.expires_at < now))
    # Only the newest link of a Telegram user is valid.
    db.session.execute(
        update(TelegramLinkToken)
        .where(
            TelegramLinkToken.telegram_user_id == telegram_user_id,
            TelegramLinkToken.used_at.is_(None),
        )
        .values(used_at=now)
    )

    token = secrets.token_urlsafe(LINK_TOKEN_BYTES)
    db.session.add(
        TelegramLinkToken(
            token_hash=hash_link_token(token),
            telegram_user_id=telegram_user_id,
            telegram_username=username,
            telegram_name=name,
            created_at=now,
            expires_at=now + timedelta(seconds=ttl_seconds),
        )
    )
    db.session.commit()
    return token


def token_expiry_timestamp(row: TelegramLinkToken) -> float:
    return _aware(row.expires_at).timestamp()


def find_valid_link_token(token_hash: str) -> TelegramLinkToken | None:
    if not isinstance(token_hash, str) or len(token_hash) != 64:
        return None
    row = TelegramLinkToken.query.filter_by(token_hash=token_hash).first()
    if row is None or row.used_at is not None or _aware(row.expires_at) <= utcnow():
        return None
    return row


def claim_link_token(token_hash: str) -> tuple[TelegramLinkToken, str] | None:
    """Swap the token from the URL for a new secret kept only in the session.

    The URL (which also lands in access logs and browser history) is dead
    from the first time it is opened; only the browser that opened it can go
    on to confirm. Returns (row, new_hash) or None when the token is invalid.
    """
    if not isinstance(token_hash, str) or len(token_hash) != 64:
        return None
    new_hash = hash_link_token(secrets.token_urlsafe(LINK_TOKEN_BYTES))
    token_id = db.session.execute(
        update(TelegramLinkToken)
        .where(
            TelegramLinkToken.token_hash == token_hash,
            TelegramLinkToken.used_at.is_(None),
            TelegramLinkToken.expires_at > utcnow(),
        )
        .values(token_hash=new_hash)
        .returning(TelegramLinkToken.id)
    ).scalar_one_or_none()
    db.session.commit()
    if token_id is None:
        return None
    return db.session.get(TelegramLinkToken, token_id), new_hash


def consume_link_token(token_hash: str) -> TelegramLinkToken | None:
    """Mark the token used, atomically; None when it was not valid.

    The conditional UPDATE is the one-time guarantee: of two concurrent
    requests with the same token exactly one gets a row back.
    """
    if not isinstance(token_hash, str) or len(token_hash) != 64:
        return None
    now = utcnow()
    token_id = db.session.execute(
        update(TelegramLinkToken)
        .where(
            TelegramLinkToken.token_hash == token_hash,
            TelegramLinkToken.used_at.is_(None),
            TelegramLinkToken.expires_at > now,
        )
        .values(used_at=now)
        .returning(TelegramLinkToken.id)
    ).scalar_one_or_none()
    if token_id is None:
        return None
    return db.session.get(TelegramLinkToken, token_id)


def link_state(user, token: TelegramLinkToken) -> str:
    """What confirming ``token`` would do for ``user``.

    "confirm", "already_linked_here", "telegram_taken" or "user_has_other".
    """
    existing = identity_for_telegram(token.telegram_user_id)
    if existing is not None:
        return "already_linked_here" if existing.user_id == user.id else "telegram_taken"
    if identity_for_user(user.id) is not None:
        return "user_has_other"
    return "confirm"


def link_with_token(user, token_hash: str) -> tuple[str, TelegramIdentity | None]:
    """Consume the token and attach its Telegram account to ``user``.

    Returns (result, identity); result is "linked", "invalid" or one of the
    non-confirm states of link_state. The token is spent in every case.
    """
    from sqlalchemy.exc import IntegrityError

    try:
        locked = lock_user(user.id)
        token = consume_link_token(token_hash)
        if locked is None or token is None:
            db.session.commit()
            return "invalid", None

        state = link_state(locked, token)
        if state != "confirm":
            db.session.commit()
            return state, None

        identity = TelegramIdentity(
            user_id=locked.id,
            telegram_user_id=token.telegram_user_id,
            telegram_username=token.telegram_username,
        )
        db.session.add(identity)
        db.session.commit()
        return "linked", identity
    except IntegrityError:
        # The same Telegram account or user was linked concurrently.
        db.session.rollback()
        consume_link_token(token_hash)
        db.session.commit()
        return "telegram_taken", None


def unlink_telegram(user) -> str:
    """"unlinked", "not_connected" or "last_method"."""
    locked = lock_user(user.id)
    identity = identity_for_user(user.id) if locked is not None else None
    if identity is None:
        db.session.rollback()
        return "not_connected"
    if remaining_methods_without(locked, "telegram") == 0:
        db.session.rollback()
        return "last_method"
    db.session.delete(identity)
    db.session.commit()
    return "unlinked"


def email_in_use(email: str) -> bool:
    return (
        db.session.query(User.id).filter(func.lower(User.email) == email.lower()).first()
        is not None
    )


# --- Bot sign-in and registration ---------------------------------------------------


def _ensure_profile(user) -> None:
    if not user.profile:
        db.session.add(
            UserProfile(user_id=user.id, training_location="home", onboarding_completed=False)
        )


def record_bot_login(identity: TelegramIdentity, username: str | None, *, restore: bool) -> None:
    """Note a sign-in through the bot.

    A restore carries only the Telegram id, so the stored username is left
    alone and an earlier /logout is not undone.
    """
    if not restore:
        if username != identity.telegram_username:
            identity.telegram_username = username
        identity.bot_logged_out_at = None
    identity.last_login_at = utcnow()
    _ensure_profile(identity.user)
    db.session.commit()


def mark_bot_logged_out(identity: TelegramIdentity) -> None:
    if identity.bot_logged_out_at is None:
        identity.bot_logged_out_at = utcnow()
        db.session.commit()


def create_account_for_telegram(
    telegram_user_id: int, email: str, *, name: str | None, username: str | None
) -> tuple[User, TelegramIdentity] | None:
    """Create the user, profile and Telegram identity in one transaction.

    None when a unique constraint stops it: the Telegram account or the
    email was taken by a concurrent request. Nothing is created then.
    """
    user = User(
        username=clean_username(name) or email.split("@")[0][:50],
        email=email,
        password=OAUTH_PASSWORD_MARKER,
        is_premium=False,
    )
    try:
        db.session.add(user)
        db.session.flush()
        db.session.add(
            UserProfile(
                user_id=user.id,
                training_location="home",
                wants_nutrition=True,
                wants_recovery=False,
                onboarding_completed=False,
            )
        )
        identity = TelegramIdentity(
            user_id=user.id,
            telegram_user_id=telegram_user_id,
            telegram_username=username,
            last_login_at=utcnow(),
        )
        db.session.add(identity)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return None
    return user, identity


# --- Emails -------------------------------------------------------------------------


def _display(username: str | None, name: str | None) -> str:
    if username:
        return f"@{username}"
    return name or "Telegram"


def send_telegram_registration_code(email: str, code: str) -> None:
    send_email(
        to=email,
        subject="Код підтвердження NosiFit (Telegram)",
        text=(
            "Хтось (імовірно ви) створює акаунт NosiFit через Telegram-бота "
            "з цією адресою.\n\n"
            f"Код підтвердження: {code}\n\n"
            "Код дійсний 10 хвилин. Введіть його лише в чаті з ботом NosiFit "
            "і нікому його не повідомляйте: з ним можна створити акаунт на "
            "вашу пошту.\n\n"
            "Якщо це були не ви — просто проігноруйте цей лист."
        ),
    )


def send_telegram_existing_account_notice(email: str) -> None:
    # Sent instead of a code when the address already has an account, so
    # the bot answers the same either way and reveals nothing.
    send_email(
        to=email,
        subject="Вхід у NosiFit через Telegram",
        text=(
            "Хтось (імовірно ви) намагався створити акаунт NosiFit через "
            "Telegram-бота з цією адресою. З нею вже пов'язаний акаунт NosiFit, "
            "тому новий акаунт не створено.\n\n"
            "Щоб користуватися ботом зі своїм акаунтом: увійдіть на сайт NosiFit, "
            "відкрийте Профіль → Підключені акаунти → «Підключити Telegram», "
            "або натисніть у боті «Підключити акаунт».\n\n"
            "Якщо це були не ви — просто проігноруйте цей лист."
        ),
    )


# Security notices: sent in the background with retries (email_outbox), so
# the page answers at once and an email-service hiccup does not lose them.


def notify_telegram_linked(user, username: str | None) -> None:
    enqueue_notice(
        "telegram_linked",
        to=user.email,
        subject="До вашого акаунта NosiFit підключено Telegram",
        text=(
            f"До вашого акаунта NosiFit підключено Telegram "
            f"({_display(username, None)}). Тепер через цього Telegram-бота "
            "можна входити у ваш акаунт.\n\n"
            "Якщо це були не ви: увійдіть на сайт, відключіть Telegram у "
            "Профіль → Підключені акаунти та змініть пароль."
        ),
    )


def notify_telegram_unlinked(user) -> None:
    enqueue_notice(
        "telegram_unlinked",
        to=user.email,
        subject="Telegram відключено від акаунта NosiFit",
        text=(
            "Від вашого акаунта NosiFit відключено Telegram. Вхід через "
            "Telegram-бота більше не працює.\n\n"
            "Якщо це були не ви, негайно змініть пароль."
        ),
    )
