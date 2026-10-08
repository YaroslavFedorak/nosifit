from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user, login_user
from backend.app.extensions import db
from backend.app.utils.validation import password_problem
from web.app.security import hit_limit, too_many_requests

password_change_bp = Blueprint("password_change", __name__)

ATTEMPT_LIMIT_PER_USER = (10, 15 * 60)


@password_change_bp.route("/profile/change_password", methods=["POST"])
@login_required
def change_password():
    old = request.form.get("current_password", "")
    new = request.form.get("new_password", "")
    confirm = request.form.get("confirm_password", "")

    if not old or not new or not confirm:
        return jsonify({"status": "error", "message": "missing_fields"}), 400

    # A stolen session must not be able to brute-force the current password.
    if hit_limit("password-change", current_user.id, *ATTEMPT_LIMIT_PER_USER):
        return too_many_requests()

    if not current_user.check_password(old):
        return jsonify({"status": "error", "message": "wrong_old"}), 400

    if new != confirm:
        return jsonify({"status": "error", "message": "mismatch"}), 400

    if password_problem(new):
        return jsonify({"status": "error", "message": "weak"}), 400

    if current_user.check_password(new):
        return jsonify({"status": "error", "message": "same"}), 400

    user = current_user._get_current_object()
    user.set_password(new)
    db.session.commit()

    # The new hash logs out every other session; keep this one signed in.
    login_user(user, remember=True)

    return jsonify({"status": "success"})
