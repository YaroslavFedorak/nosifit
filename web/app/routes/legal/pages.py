"""/privacy (the privacy policy) and /consent (giving the consent it asks for).

The policy text lives in templates/legal/privacy_<locale>.html: Ukrainian and
English; other interface languages show the English text. Who is responsible
for the data comes from PRIVACY_CONTROLLER_NAME / PRIVACY_CONTACT_EMAIL.
"""

from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user

from backend.app.services.consent import (
    CONSENT_VERSION,
    POLICY_DATE,
    age_confirmed,
    consent_given,
    has_current_consent,
    record_consent,
    too_young,
)
from backend.app.services.account_service import withdraw_consent
from backend.app.services.data_export import export_user_data
from backend.app.utils.validation import MIN_ACCOUNT_AGE

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


@legal_bp.get("/privacy/my-data")
def my_data():
    """Download everything stored about me. Works without consent: access to
    one's own data never depends on agreeing to anything."""
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    response = jsonify(export_user_data(current_user))
    response.headers["Content-Disposition"] = 'attachment; filename="nosifit-my-data.json"'
    response.headers["Cache-Control"] = "no-store"
    return response


@legal_bp.route("/consent/withdraw", methods=["GET", "POST"])
def withdraw():
    """Withdraw the health-data consent (account_service.withdraw_consent).

    One confirmation, no password or emailed code: withdrawing must be as
    easy as giving consent. The page says exactly what is erased and what
    stays, and offers the data download first.
    """
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        if request.form.get("confirm_erase") != "on":
            flash("Підтвердіть, що розумієте, які дані буде видалено.", "error")
            return redirect(url_for("legal.withdraw"))
        withdraw_consent(current_user._get_current_object())
        flash("Згоду відкликано, записи про здоров'я видалено. Обліковий запис залишився.", "success")
        return redirect(url_for("legal.consent"))
    return render_template("legal/withdraw.html", consented=has_current_consent(current_user))


@legal_bp.route("/consent", methods=["GET", "POST"])
def consent():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))

    next_url = _safe_next(request.values.get("next"))
    if request.method == "POST":
        if too_young(current_user):
            flash(f"nosifit доступний з {MIN_ACCOUNT_AGE} років: у профілі вказано менший вік.", "error")
            return redirect(url_for("legal.consent", next=next_url))
        if not (consent_given(request.form) and age_confirmed(request.form)):
            flash("Щоб користуватися nosifit, потрібні обидві згоди та підтвердження віку.", "error")
            return redirect(url_for("legal.consent", next=next_url))
        record_consent(current_user)
        return redirect(next_url)

    if has_current_consent(current_user):
        return redirect(next_url)
    return render_template(
        "legal/consent.html",
        next_url=next_url,
        min_age=MIN_ACCOUNT_AGE,
        under_age=too_young(current_user),
        **_policy_context(),
    )
