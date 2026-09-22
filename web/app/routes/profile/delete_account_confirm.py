from flask import Blueprint, request, session, jsonify
from flask_login import login_required, current_user

delete_confirm_bp = Blueprint("delete_confirm", __name__)


@delete_confirm_bp.route("/profile/delete/confirm", methods=["POST"])
@login_required
def confirm_delete():
    data = request.get_json(silent=True) or {}
    code = data.get("code")

    if "delete_code" not in session:
        return jsonify({"status": "expired"}), 400

    if session.get("delete_code_email") != current_user.email:
        return jsonify({"status": "email_mismatch"}), 400

    if code is None or str(code) != str(session["delete_code"]):
        return jsonify({"status": "wrong"}), 400

    return jsonify({"status": "ok"})
