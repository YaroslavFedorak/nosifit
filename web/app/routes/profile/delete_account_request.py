from flask import Blueprint, session, jsonify
from flask_login import login_required, current_user
from web.app.utils.mailer import send_email_code
import random

delete_request_bp = Blueprint("delete_request", __name__)


@delete_request_bp.route("/profile/delete/request", methods=["POST"])
@login_required
def request_delete():
    code = random.randint(100000, 999999)

    session["delete_code"] = code
    session["delete_code_email"] = current_user.email

    send_email_code(current_user.email, code)

    return jsonify({"status": "sent"})
