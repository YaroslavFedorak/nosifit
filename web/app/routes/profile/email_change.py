from flask import Blueprint, request, jsonify, session
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from backend.app.extensions import db
from backend.app.models.user import User
from backend.app.utils.codes import new_code, store_session_code, verify_session_code
from backend.app.utils.mailer import EmailSendError, send_email_code
from backend.app.utils.validation import normalize_email
from web.app.security import hit_limit, too_many_requests

email_change_bp = Blueprint("email_change", __name__)

SESSION_KEY = "email_change"
SEND_LIMIT_PER_USER = (5, 60 * 60)


def _email_taken(email) -> bool:
    return (
        User.query.filter(db.func.lower(User.email) == email, User.id != current_user.id).first()
        is not None
    )


@email_change_bp.route("/profile/change_email", methods=["POST"])
@login_required
def change_email():
    data = request.get_json(silent=True) or {}
    raw_email = data.get("new_email")
    new_email = normalize_email(raw_email if isinstance(raw_email, str) else None)

    if not new_email:
        return jsonify({"status": "error", "message": "missing_email"}), 400

    if new_email == current_user.email.lower():
        return jsonify({"status": "error", "message": "same_email"}), 400

    if _email_taken(new_email):
        return jsonify({"status": "error", "message": "email_taken"}), 400

    if hit_limit("email-change-send", current_user.id, *SEND_LIMIT_PER_USER):
        return too_many_requests()

    code = new_code()

    try:
        send_email_code(new_email, code)
    except EmailSendError:
        return jsonify({"status": "error", "message": "send_failed"}), 503

    store_session_code(SESSION_KEY, code, target=new_email, user_id=current_user.id)

    return jsonify({"status": "sent"})


@email_change_bp.route("/profile/confirm_email", methods=["POST"])
@login_required
def confirm_email():
    data = request.get_json(silent=True) or {}
    raw_code = data.get("code")

    entry = session.get(SESSION_KEY)
    if not isinstance(entry, dict) or entry.get("user_id") != current_user.id:
        session.pop(SESSION_KEY, None)
        return jsonify({"status": "error", "message": "expired"}), 400

    result = verify_session_code(SESSION_KEY, raw_code, current_user.id)
    if result == "expired":
        return jsonify({"status": "error", "message": "expired"}), 400
    if result != "ok":
        return jsonify({"status": "error", "message": "wrong"}), 400

    new_email = normalize_email(entry.get("target"))
    session.pop(SESSION_KEY, None)

    if not new_email:
        return jsonify({"status": "error", "message": "expired"}), 400

    if _email_taken(new_email):
        return jsonify({"status": "error", "message": "email_taken"}), 400

    current_user.email = new_email
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"status": "error", "message": "email_taken"}), 400

    return jsonify({"status": "success"})
