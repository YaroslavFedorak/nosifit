from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from backend.app.utils.codes import new_code, store_session_code
from backend.app.utils.mailer import EmailSendError, send_email_code
from web.app.security import hit_limit, too_many_requests

delete_request_bp = Blueprint("delete_request", __name__)

SESSION_KEY = "delete_code"
SEND_LIMIT_PER_USER = (5, 60 * 60)


@delete_request_bp.route("/profile/delete/request", methods=["POST"])
@login_required
def request_delete():
    if hit_limit("delete-send", current_user.id, *SEND_LIMIT_PER_USER):
        return too_many_requests()

    code = new_code()

    try:
        send_email_code(current_user.email, code)
    except EmailSendError:
        return jsonify({"status": "send_failed"}), 503

    store_session_code(
        SESSION_KEY,
        code,
        email=current_user.email,
        user_id=current_user.id,
        verified=False,
    )

    return jsonify({"status": "sent"})
