"""Connecting a Telegram account to an existing NosiFit account.

1. The bot asks /api/telegram/link-token for a one-time link bound to the
   Telegram user id and sends it to that user.
2. GET /auth/telegram/link/<token> swaps the token for a new secret kept
   only in this browser's session (the URL stops working at once, so a copy
   from logs or history is useless) and redirects to a URL without it.
3. Not signed in -> normal login (password, Google, GitHub); the pending link
   survives it. Linking never happens because an email matches.
4. Signed in within the last 15 minutes (else: sign in again) -> a page that
   names both the Telegram account and the NosiFit account; only the POST
   from its Confirm button links them. The form carries a per-session token
   on top of the Origin check.

Every invalid, used, expired or forged token gets the same page.
"""

import hmac
import logging

from flask import (
    Blueprint,
    flash,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from backend.app.extensions import db
from backend.app.services import telegram_auth as tg
from web.app.routes.auth.telegram_session import (
    clear_pending_link,
    get_pending_link,
    is_recently_authenticated,
    is_telegram_session,
    set_pending_link,
)
from web.app.security import client_ip, hit_limit, too_many_requests

logger = logging.getLogger(__name__)

telegram_link_bp = Blueprint("telegram_link", __name__, url_prefix="/auth/telegram")

OPEN_LIMIT_PER_IP = (30, 15 * 60)
CONFIRM_LIMIT_PER_USER = (10, 15 * 60)
CONFIRM_LIMIT_PER_IP = (30, 15 * 60)


def _invalid(status=400):
    clear_pending_link()
    return make_response(render_template("auth/telegram_link.html", state="invalid"), status)


def _no_referrer(response):
    # The token is in this URL; keep it out of Referer headers.
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@telegram_link_bp.get("/link/<token>")
def open_link(token):
    if hit_limit("tg-link-open-ip", client_ip(), *OPEN_LIMIT_PER_IP):
        return _no_referrer(too_many_requests())

    if not tg.is_link_token_format(token):
        return _no_referrer(_invalid())

    claimed = tg.claim_link_token(tg.hash_link_token(token))
    if claimed is None:
        return _no_referrer(_invalid())

    row, session_hash = claimed
    set_pending_link(session_hash, tg.token_expiry_timestamp(row))
    return _no_referrer(redirect(url_for("telegram_link.link_page")))


@telegram_link_bp.get("/link")
def link_page():
    pending = get_pending_link()
    row = tg.find_valid_link_token(pending["h"]) if pending else None
    if row is None:
        return _invalid()

    if not current_user.is_authenticated:
        flash("Увійдіть у свій акаунт NosiFit, щоб підключити Telegram.", "info")
        return redirect(url_for("auth.login"))

    if not is_recently_authenticated():
        return _sign_in_again()

    return render_template(
        "auth/telegram_link.html",
        state=tg.link_state(current_user, row),
        telegram_username=row.telegram_username,
        telegram_name=row.telegram_name,
        account_email=current_user.email,
        account_username=current_user.username,
        csrf_token=pending["csrf"],
    )


def _sign_in_again():
    flash("Для безпеки увійдіть ще раз, щоб підтвердити підключення Telegram.", "info")
    return redirect(url_for("auth.login"))


def _form_token_ok(pending) -> bool:
    given = request.form.get("csrf_token")
    return (
        pending is not None
        and isinstance(given, str)
        and hmac.compare_digest(given, pending["csrf"])
    )


@telegram_link_bp.post("/link/confirm")
@login_required
def confirm_link():
    if is_telegram_session():  # unreachable (scope guard); defence in depth
        return _invalid(403)

    if hit_limit("tg-link-confirm-ip", client_ip(), *CONFIRM_LIMIT_PER_IP) or hit_limit(
        "tg-link-confirm-user", current_user.id, *CONFIRM_LIMIT_PER_USER
    ):
        return too_many_requests()

    pending = get_pending_link()
    if not _form_token_ok(pending):
        return _invalid()

    if not is_recently_authenticated():
        return _sign_in_again()

    clear_pending_link()
    user = current_user._get_current_object()
    result, identity = tg.link_with_token(user, pending["h"])

    if result == "invalid":
        return _invalid()
    if result != "linked":
        return render_template("auth/telegram_link.html", state=result), 409

    logger.info("Telegram connected to user %s", user.id)
    tg.notify_telegram_linked(user, identity.telegram_username)
    return render_template(
        "auth/telegram_link.html",
        state="linked",
        telegram_username=identity.telegram_username,
    )


@telegram_link_bp.post("/link/cancel")
def cancel_link():
    pending = get_pending_link()
    if _form_token_ok(pending):
        tg.consume_link_token(pending["h"])
        db.session.commit()
    clear_pending_link()
    return render_template("auth/telegram_link.html", state="cancelled")
