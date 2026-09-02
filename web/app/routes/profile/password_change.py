from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from web.app import db

password_change_bp = Blueprint("password_change", __name__)


@password_change_bp.route("/profile/change_password", methods=["POST"])
@login_required
def change_password():
    data = request.json
    old = data.get("old_password")
    new = data.get("new_password")
    confirm = data.get("confirm_password")

    if not check_password_hash(current_user.password, old):
        return jsonify({"status": "error", "message": "wrong_old"}), 400

    if new != confirm:
        return jsonify({"status": "error", "message": "mismatch"}), 400

    if check_password_hash(current_user.password, new):
        return jsonify({"status": "error", "message": "same"}), 400

    current_user.password = generate_password_hash(new)
    db.session.commit()

    return jsonify({"status": "success"})
