from flask import Blueprint, request, jsonify, session
from flask_login import login_required, current_user
from backend.app.utils.mailer import send_email_code
from backend.app.extensions import db
import random

email_change_bp = Blueprint("email_change", __name__)


@email_change_bp.route("/profile/change_email", methods=["POST"])
@login_required
def change_email():
    data = request.get_json(silent=True) or {}
    new_email = data.get("new_email", "").strip()

    if not new_email:
        return jsonify({"status": "error", "message": "missing_email"}), 400

    if new_email == current_user.email:
        return jsonify({"status": "error", "message": "same_email"}), 400

    code = random.randint(100000, 999999)

    session["email_change_code"] = code
    session["email_change_target"] = new_email

    send_email_code(new_email, code)

    return jsonify({"status": "sent"})


@email_change_bp.route("/profile/confirm_email", methods=["POST"])
@login_required
def confirm_email():
    data = request.get_json(silent=True) or {}
    raw_code = data.get("code")

    if "email_change_code" not in session:
        return jsonify({"status": "error", "message": "expired"}), 400

    if raw_code is None:
        return jsonify({"status": "error", "message": "wrong"}), 400

    try:
        code = int(raw_code)
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "wrong"}), 400

    if code != session["email_change_code"]:
        return jsonify({"status": "error", "message": "wrong"}), 400

    new_email = session.get("email_change_target")

    if not new_email:
        session.pop("email_change_code", None)
        session.pop("email_change_target", None)

        return jsonify({"status": "error", "message": "expired"}), 400

    current_user.email = new_email
    db.session.commit()

    session.pop("email_change_code", None)
    session.pop("email_change_target", None)

    return jsonify({"status": "success"})


