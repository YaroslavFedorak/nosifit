"""Consent gate: no use of the service without the current consent.

A signed-in user who has not accepted the current privacy policy and given
explicit consent to processing health data (backend/app/services/consent.py)
can still sign in and out, read the policy, give consent, use public pages
and delete the account, but nothing else:

- pages answer with a redirect to /consent (and back afterwards);
- the JSON API and form posts answer 403 {"code": "consent_required"}; the
  Telegram bot shows its /consent command for it.

Applies to every way in: website, Google/GitHub, Telegram, sessions that
existed before consent was recorded.
"""

from flask import jsonify, redirect, request, url_for
from flask_login import current_user

from backend.app.services.consent import has_current_consent

V1_SUFFIX = "_v1"

# Blueprints usable without consent (names without the /api/v1 "_v1").
OPEN_BLUEPRINTS = frozenset(
    {
        "auth",  # sign in / out, password reset
        "google_oauth",
        "github",
        "email_verification",
        "complete_profile",
        "telegram_link",
        "telegram_api",  # bot-signed sign-in endpoints
        "root",
        "public",
        "info",
        "legal",  # /privacy, /consent
        "consent_api",
        "i18n",
        "delete_request",  # deleting the account is always possible
        "delete_confirm",
        "delete_final",
    }
)
OPEN_ENDPOINTS = frozenset({"static", "static_unversioned", "healthz"})


def _blueprint() -> str:
    return (request.blueprint or "").removesuffix(V1_SUFFIX)


def enforce_consent():
    """before_request: stop signed-in users without the current consent."""
    if request.endpoint is None or request.endpoint in OPEN_ENDPOINTS:
        return None
    if _blueprint() in OPEN_BLUEPRINTS:
        return None
    if not current_user.is_authenticated or has_current_consent(current_user):
        return None

    wants_page = (
        request.method in ("GET", "HEAD")
        and not request.path.startswith("/api/")
        and not request.is_json
    )
    if wants_page:
        return redirect(url_for("legal.consent", next=request.full_path.rstrip("?")))
    response = jsonify(
        {"error": "Consent to the privacy policy is required", "code": "consent_required"}
    )
    response.status_code = 403
    return response
