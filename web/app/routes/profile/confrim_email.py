from flask import Blueprint, request, jsonify, session
from flask_login import login_required, current_user
from web.app import db

confirm_email_bp = Blueprint("confirm_email", __name__)


@confirm_email_bp.route("/profile/confirm_email", methods=["POST"])
@login_required
def confirm_email():
    data = request.json
    code = int(data.get("code"))

    if "email_change_code" not in session:
        return jsonify({"status": "error", "message": "expired"}), 400

    if code != session["email_change_code"]:
        return jsonify({"status": "error", "message": "wrong"}), 400

    current_user.email = session["email_change_target"]
    db.session.commit()

    session.pop("email_change_code")
    session.pop("email_change_target")

    return jsonify({"status": "success"})
