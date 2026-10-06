from flask import Blueprint, session, jsonify
from flask_login import login_required, current_user
from backend.app.utils.codes import hash_code, new_code
from backend.app.utils.mailer import EmailSendError, send_email_code

delete_request_bp = Blueprint("delete_request", __name__)


@delete_request_bp.route("/profile/delete/request", methods=["POST"])
@login_required
def request_delete():
    code = new_code()

    try:
        send_email_code(current_user.email, code)
    except EmailSendError:
        return jsonify({"status": "send_failed"}), 503

    session["delete_code"] = hash_code(code)
    session["delete_code_email"] = current_user.email

    return jsonify({"status": "sent"})

