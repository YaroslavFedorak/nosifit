"""Endpoints only the Telegram bot can call.

Every request is signed with TELEGRAM_BOT_API_SECRET (see
shared.bot_signature). The Telegram user id in the body comes
from the Telegram update the bot received, so the signature is what lets
the server trust it; without the secret nobody can claim a Telegram id.

No NosiFit password ever passes through here. Limits are per Telegram user
and per email, not per IP: all bot traffic comes from one address.
"""

import functools
import logging
import re
import secrets

from flask import Blueprint, current_app, jsonify, request

from backend.app.services import telegram_auth as tg
from backend.app.utils.bot_signature import MAX_SKEW_SECONDS, check_signature
from backend.app.utils.mailer import EmailSendError
from backend.app.utils.validation import normalize_email
from backend.app.services.telegram_auth import LINK_SIGN_IN_METHODS
from backend.app.services.verification_codes import (
    MAX_CODE_ATTEMPTS,
    SEND_LIMIT_PER_EMAIL,
    VERIFY_ATTEMPT_WINDOW,
    active_code,
    clear_codes,
    issue_code,
    spend_code,
)
from backend.app.utils.rate_limit import hit_limit, reset_limit
from auth.telegram_session import start_telegram_session

logger = logging.getLogger(__name__)

telegram_api_bp = Blueprint("telegram_api", __name__, url_prefix="/api/telegram")

MAX_BODY_BYTES = 4096
_CODE_RE = re.compile(r"^\d{6}$")

LOGIN_LIMIT_PER_TELEGRAM = (20, 15 * 60)
REGISTER_LIMIT_PER_TELEGRAM = (5, 60 * 60)
# Protects the email quota (Brevo free plan: 300/day) from one abuser
# rotating Telegram accounts.
REGISTER_LIMIT_GLOBAL = (100, 60 * 60)
VERIFY_LIMIT_PER_TELEGRAM = (10, 10 * 60)
LINK_LIMIT_PER_TELEGRAM = (5, 15 * 60)


def _error(code: str, status: int):
    response = jsonify({"error": code, "code": code})
    response.status_code = status
    return response


def bot_signed(view):
    """Verify the bot's signature and pass the Telegram user id and body."""

    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        secret = current_app.config.get("TELEGRAM_BOT_API_SECRET")
        if not secret:
            # Feature switched off: look like any unknown URL.
            return _error("not_found", 404)

        if (request.content_length or 0) > MAX_BODY_BYTES:
            return _error("payload_too_large", 413)
        body = request.get_data(cache=True)
        if len(body) > MAX_BODY_BYTES:
            return _error("payload_too_large", 413)

        nonce = check_signature(secret, request.headers, request.method, request.path, body)
        if nonce is None:
            logger.warning("Rejected unsigned or badly signed bot request to %s", request.path)
            return _error("unauthorized", 401)
        # A nonce is good once; the window covers the allowed clock skew.
        if hit_limit("bot-nonce", nonce, 1, 2 * MAX_SKEW_SECONDS + 5):
            logger.warning("Rejected replayed bot request to %s", request.path)
            return _error("unauthorized", 401)

        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return _error("invalid_request", 400)

        telegram_user_id = tg.parse_telegram_user_id(data.get("telegram_user_id"))
        if telegram_user_id is None:
            return _error("invalid_telegram_user", 400)

        return view(telegram_user_id, data, *args, **kwargs)

    return wrapper


def _base_url() -> str | None:
    base = (current_app.config.get("PUBLIC_BASE_URL") or "").rstrip("/")
    if base:
        return base
    if current_app.config.get("IS_PRODUCTION"):
        # Never build links from the request's Host header in production.
        return None
    return request.host_url.rstrip("/")


# --- Sign in --------------------------------------------------------------------------


@telegram_api_bp.post("/login")
@bot_signed
def telegram_login(telegram_user_id, data):
    if hit_limit("tg-login", telegram_user_id, *LOGIN_LIMIT_PER_TELEGRAM):
        return _error("rate_limited", 429)

    identity = tg.identity_for_telegram(telegram_user_id)
    if identity is None or identity.user is None:
        return _error("not_linked", 404)

    # "restore": the bot lost its session (restart) and reopens it without
    # the user pressing "Log in" - unless they logged out in the bot. It
    # carries only the id, so the stored username is left alone.
    restore = data.get("restore") is True
    if restore and identity.bot_logged_out_at is not None:
        return _error("logged_out", 401)

    user = identity.user
    username = None if restore else tg.clean_telegram_username(data.get("username"))
    tg.record_bot_login(identity, username, restore=restore)

    start_telegram_session(user, identity)
    return jsonify({"status": "ok", "username": user.username})


@telegram_api_bp.post("/logout")
@bot_signed
def telegram_logout(telegram_user_id, data):
    """/logout in the bot: no session restore until the next explicit login."""
    identity = tg.identity_for_telegram(telegram_user_id)
    if identity is not None:
        tg.mark_bot_logged_out(identity)
    return jsonify({"status": "ok"})


# --- Create an account ---------------------------------------------------------------


@telegram_api_bp.post("/register/start")
@bot_signed
def register_start(telegram_user_id, data):
    if hit_limit("tg-register-user", telegram_user_id, *REGISTER_LIMIT_PER_TELEGRAM):
        return _error("rate_limited", 429)

    if tg.identity_for_telegram(telegram_user_id) is not None:
        return _error("already_linked", 409)

    raw_email = data.get("email")
    email = normalize_email(raw_email if isinstance(raw_email, str) else None)
    if not email:
        return _error("invalid_email", 400)

    # Counted the same way whether or not the address has an account.
    if hit_limit("verify-send-email", email, *SEND_LIMIT_PER_EMAIL) or hit_limit(
        "tg-register-global", "all", *REGISTER_LIMIT_GLOBAL
    ):
        return _error("rate_limited", 429)

    try:
        if tg.email_in_use(email):
            # No code: an existing account is never attached by email.
            tg.send_telegram_existing_account_notice(email)
        else:
            code = issue_code(email)
            tg.send_telegram_registration_code(email, code)
    except EmailSendError:
        return _error("send_failed", 503)

    # Identical answer in both cases: the bot cannot tell whether the
    # address is registered.
    return jsonify({"status": "code_sent"})


@telegram_api_bp.post("/register/verify")
@bot_signed
def register_verify(telegram_user_id, data):
    if hit_limit("tg-verify-user", telegram_user_id, *VERIFY_LIMIT_PER_TELEGRAM):
        return _error("too_many_attempts", 429)

    raw_email = data.get("email")
    email = normalize_email(raw_email if isinstance(raw_email, str) else None)
    raw_code = data.get("code")
    code = raw_code.strip() if isinstance(raw_code, str) else ""
    if not email:
        return _error("invalid_code", 400)

    if tg.identity_for_telegram(telegram_user_id) is not None:
        return _error("already_linked", 409)

    # Shared with the web form: wrong codes for one address are counted
    # together, whichever client sends them.
    if hit_limit("verify-attempts", email, MAX_CODE_ATTEMPTS, VERIFY_ATTEMPT_WINDOW):
        clear_codes(email)
        return _error("too_many_attempts", 429)

    record = active_code(email)

    # Missing, expired and wrong codes look the same.
    if (
        record is None
        or not _CODE_RE.match(code)
        or not secrets.compare_digest(str(record.code), code)
    ):
        return _error("invalid_code", 400)

    # Spend the code exactly once even under concurrent requests.
    if not spend_code(record):
        return _error("invalid_code", 400)
    reset_limit("verify-attempts", email)

    if tg.email_in_use(email):
        # Registered meanwhile (e.g. on the website). Never attach by email.
        return _error("email_unavailable", 409)

    created = tg.create_account_for_telegram(
        telegram_user_id,
        email,
        name=tg.clean_telegram_name(data.get("name")),
        username=tg.clean_telegram_username(data.get("username")),
    )
    if created is None:
        if tg.identity_for_telegram(telegram_user_id) is not None:
            return _error("already_linked", 409)
        return _error("email_unavailable", 409)
    user, identity = created

    start_telegram_session(user, identity)
    response = jsonify({"status": "created", "username": user.username})
    response.status_code = 201
    return response


# --- Connect an existing account -----------------------------------------------------


@telegram_api_bp.post("/link-token")
@bot_signed
def link_token(telegram_user_id, data):
    if hit_limit("tg-link-token", telegram_user_id, *LINK_LIMIT_PER_TELEGRAM):
        return _error("rate_limited", 429)

    if tg.identity_for_telegram(telegram_user_id) is not None:
        return _error("already_linked", 409)

    base_url = _base_url()
    if base_url is None:
        logger.error("PUBLIC_BASE_URL is not set; refusing to build a Telegram link")
        return _error("unavailable", 503)

    ttl = tg.link_token_ttl(current_app.config)
    token = tg.issue_link_token(
        telegram_user_id,
        username=tg.clean_telegram_username(data.get("username")),
        name=tg.clean_telegram_name(data.get("name")),
        ttl_seconds=ttl,
    )
    via = data.get("via") if data.get("via") in LINK_SIGN_IN_METHODS else None
    url = base_url + tg.link_page_path(token, via)
    return jsonify({"url": url, "expires_in": ttl})
