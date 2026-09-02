from flask import Blueprint, request, jsonify, session
from flask_login import login_required, current_user
from web.app.utils.mailer import send_email_code
from web.app import db
import random

email_change_bp = Blueprint("email_change", __name__)


@email_change_bp.route("/profile/change_email", methods=["POST"])
@login_required
def change_email():
    data = request.json
    new_email = data.get("new_email")

    code = random.randint(100000, 999999)
    session["email_change_code"] = code
    session["email_change_target"] = new_email

    send_email_code(new_email, code)

    return jsonify({"status": "sent"})


@email_change_bp.route("/profile/confirm_email", methods=["POST"])
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
