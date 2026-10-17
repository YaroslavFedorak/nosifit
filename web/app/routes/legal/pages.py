"""/privacy (the privacy policy) and /consent (giving the consent it asks for).

The policy text lives in templates/legal/privacy_<locale>.html: Ukrainian and
English; other interface languages show the English text. Who is responsible
for the data comes from PRIVACY_CONTROLLER_NAME / PRIVACY_CONTACT_EMAIL.
"""

from flask import Blueprint, current_app, flash, g, redirect, render_template, request, url_for
from flask_login import current_user

from backend.app.services.consent import (
    CONSENT_VERSION,
    POLICY_DATE,
    consent_given,
    has_current_consent,
    record_consent,
)

legal_bp = Blueprint("legal", __name__)

POLICY_LOCALES = ("uk", "en")


def _policy_locale(locale: str) -> str:
    return locale if locale in POLICY_LOCALES else "en"


def _policy_context():
    return {
        "controller_name": current_app.config.get("PRIVACY_CONTROLLER_NAME") or "",
        "contact_email": current_app.config.get("PRIVACY_CONTACT_EMAIL") or "",
        "policy_date": POLICY_DATE,
        "consent_version": CONSENT_VERSION,
    }


def _safe_next(value) -> str:
    # Only paths on this site: "/x", never "//host" or "/\\host".
    if isinstance(value, str) and value.startswith("/") and not value.startswith(("//", "/\\")):
        return value
    return url_for("dashboard.dashboard")


@legal_bp.get("/privacy")
def privacy():
    return render_template(
        "legal/privacy.html",
        policy_locale=_policy_locale(getattr(g, "locale", "en")),
        **_policy_context(),
    )


@legal_bp.route("/consent", methods=["GET", "POST"])
def consent():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))

    next_url = _safe_next(request.values.get("next"))
    if request.method == "POST":
        if not consent_given(request.form):
            flash("Щоб користуватися NosiFit, потрібні обидві згоди.", "error")
            return redirect(url_for("legal.consent", next=next_url))
        record_consent(current_user)
        return redirect(next_url)

    if has_current_consent(current_user):
        return redirect(next_url)
    return render_template("legal/consent.html", next_url=next_url, **_policy_context())
