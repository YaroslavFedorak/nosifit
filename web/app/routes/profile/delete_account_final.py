from flask import Blueprint, request, session, jsonify
from flask_login import login_required, current_user, logout_user

from backend.app.services.account_service import delete_user_account
from backend.app.utils.codes import load_session_code
from web.app.routes.profile.delete_account_confirm import pending_deletion
from web.app.routes.profile.delete_account_request import SESSION_KEY

delete_final_bp = Blueprint("delete_final", __name__)


@delete_final_bp.route("/profile/delete/final", methods=["POST"])
@login_required
def delete_final():
    data = request.get_json(silent=True) or {}

    email = data.get("email") if isinstance(data.get("email"), str) else ""
    password = data.get("password") if isinstance(data.get("password"), str) else ""

    if load_session_code(SESSION_KEY) is None:
        return jsonify({"status": "expired"}), 400

    entry = pending_deletion()
    if entry is None:
        return jsonify({"status": "email_mismatch"}), 400

    if not entry.get("verified"):
        return jsonify({"status": "expired"}), 400

    if email.strip().lower() != current_user.email.lower():
        return jsonify({"status": "email_mismatch"}), 400

    # Google/GitHub accounts have no password; the emailed code proves
    # control of the account for them.
    if current_user.has_password and not current_user.check_password(password):
        return jsonify({"status": "wrong_password"}), 400

    delete_user_account(current_user._get_current_object())

    logout_user()
    session.clear()

    return jsonify({"status": "deleted"})
