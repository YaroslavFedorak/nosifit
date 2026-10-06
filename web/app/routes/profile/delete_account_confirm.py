from flask import Blueprint, request, session, jsonify
from flask_login import login_required, current_user

from backend.app.utils.codes import verify_session_code
from web.app.routes.profile.delete_account_request import SESSION_KEY

delete_confirm_bp = Blueprint("delete_confirm", __name__)


def pending_deletion():
    """The deletion request of the signed-in user, or None."""
    entry = session.get(SESSION_KEY)
    if (
        not isinstance(entry, dict)
        or entry.get("user_id") != current_user.id
        or entry.get("email") != current_user.email
    ):
        return None
    return entry


@delete_confirm_bp.route("/profile/delete/confirm", methods=["POST"])
@login_required
def confirm_delete():
    data = request.get_json(silent=True) or {}
    code = data.get("code")

    entry = pending_deletion()
    if entry is None:
        if SESSION_KEY in session:
            return jsonify({"status": "email_mismatch"}), 400
        return jsonify({"status": "expired"}), 400

    result = verify_session_code(SESSION_KEY, code, current_user.id)
    if result == "expired":
        return jsonify({"status": "expired"}), 400
    if result != "ok":
        return jsonify({"status": "wrong"}), 400

    # The final step checks this flag, so it cannot skip the emailed code.
    entry["verified"] = True
    session[SESSION_KEY] = entry
    return jsonify({"status": "ok"})
