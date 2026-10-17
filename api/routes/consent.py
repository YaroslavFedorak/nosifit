"""POST /api/consent: accept the privacy policy and the processing of health
data in one call, for clients without the /consent page (the Telegram bot).

Both flags must be true: the bot shows the policy link and asks for both
explicitly. Allowed for Telegram sessions (auth/telegram_session.py).
"""

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from backend.app.services.consent import CONSENT_VERSION, consent_given, record_consent

consent_api = Blueprint("consent_api", __name__, url_prefix="/api/consent")


@consent_api.post("")
@login_required
def give_consent():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not consent_given(data):
        return jsonify({"error": "Both consents are required", "code": "consent_missing"}), 400
    record_consent(current_user)
    return jsonify({"status": "ok", "consent_version": CONSENT_VERSION})
