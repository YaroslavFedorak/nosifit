from flask import Blueprint, request, jsonify, session
from flask_login import login_required, current_user
from backend.app.extensions import db
from backend.app.models.user import User
from backend.app.utils.codes import check_code, hash_code, new_code
from backend.app.utils.mailer import EmailSendError, send_email_code

email_change_bp = Blueprint("email_change", __name__)


@email_change_bp.route("/profile/change_email", methods=["POST"])
@login_required
def change_email():
    data = request.get_json(silent=True) or {}
    new_email = (data.get("new_email") or "").strip().lower()

    if not new_email:
        return jsonify({"status": "error", "message": "missing_email"}), 400

    if new_email == current_user.email:
        return jsonify({"status": "error", "message": "same_email"}), 400

    if User.query.filter_by(email=new_email).first():
        return jsonify({"status": "error", "message": "email_taken"}), 400

    code = new_code()

    try:
        send_email_code(new_email, code)
    except EmailSendError:
        return jsonify({"status": "error", "message": "send_failed"}), 503

    session["email_change_code"] = hash_code(code)
    session["email_change_target"] = new_email

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

    if not check_code(session["email_change_code"], raw_code):
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


