"""POST /api/consent: accept the privacy policy and the processing of health
data in one call, for clients without the /consent page (the Telegram bot).

privacy_consent, health_consent and age_confirmed must all be true: the bot
shows the policy link, the minimum age and both consents explicitly. Allowed for Telegram sessions (auth/telegram_session.py).
"""

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from backend.app.services.account_service import withdraw_consent
from backend.app.services.consent import (
    CONSENT_VERSION,
    age_confirmed,
    consent_given,
    record_consent,
    too_young,
)

consent_api = Blueprint("consent_api", __name__, url_prefix="/api/consent")


@consent_api.post("")
@login_required
def give_consent():
    data = request.get_json(silent=True)
    if too_young(current_user):
        return jsonify({"error": "Under the minimum age", "code": "under_minimum_age"}), 403
    if not isinstance(data, dict) or not (consent_given(data) and age_confirmed(data)):
        return jsonify(
            {"error": "Both consents and the age confirmation are required", "code": "consent_missing"}
        ), 400
    record_consent(current_user)
    return jsonify({"status": "ok", "consent_version": CONSENT_VERSION})


@consent_api.delete("")
@login_required
def withdraw():
    """Withdraw the health-data consent: its records are erased, the account
    stays. ``confirm_erase`` must be true (the bot asks first)."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or data.get("confirm_erase") is not True:
        return jsonify({"error": "Confirm that the records will be erased", "code": "confirm_erase_required"}), 400
    withdraw_consent(current_user._get_current_object())
    return jsonify({"status": "withdrawn"})
