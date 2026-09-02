from flask import Blueprint, request, session, jsonify
from flask_login import login_required, current_user, logout_user
from web.app import db
from werkzeug.security import check_password_hash

delete_final_bp = Blueprint("delete_final", __name__)


@delete_final_bp.route("/profile/delete/final", methods=["POST"])
@login_required
def delete_final():
    email = request.json.get("email")
    password = request.json.get("password")

    if "delete_code" not in session:
        return jsonify({"status": "expired"}), 400

    if email != current_user.email:
        return jsonify({"status": "email_mismatch"}), 400

    if not check_password_hash(current_user.password, password):
        return jsonify({"status": "wrong_password"}), 400

    db.session.delete(current_user)
    db.session.commit()

    session.pop("delete_code", None)
    session.pop("delete_code_email", None)

    logout_user()

    return jsonify({"status": "deleted"})
