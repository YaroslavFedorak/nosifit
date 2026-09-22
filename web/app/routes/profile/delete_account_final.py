from flask import Blueprint, request, session, jsonify
from flask_login import login_required, current_user, logout_user
from werkzeug.security import check_password_hash
from backend.app.extensions import db
from backend.app.models.user import User
from backend.app.models.user_injury import UserInjury

delete_final_bp = Blueprint("delete_final", __name__)


@delete_final_bp.route("/profile/delete/final", methods=["POST"])
@login_required
def delete_final():
    data = request.get_json(silent=True) or {}

    email = data.get("email", "").strip()
    password = data.get("password", "")

    if "delete_code" not in session:
        return jsonify({"status": "expired"}), 400

    if session.get("delete_code_email") != current_user.email:
        return jsonify({"status": "email_mismatch"}), 400

    if email != current_user.email:
        return jsonify({"status": "email_mismatch"}), 400

    if not password:
        return jsonify({"status": "wrong_password"}), 400

    if not check_password_hash(current_user.password, password):
        return jsonify({"status": "wrong_password"}), 400

    user = db.session.get(User, current_user.id)

    if user is None:
        return jsonify({"status": "not_found"}), 404

    profile = user.profile

    if profile is not None:
        db.session.delete(profile)

    training_goals = user.training_goals

    if training_goals is not None:
        db.session.delete(training_goals)

    user_injuries = UserInjury.query.filter_by(user_id=user.id).all()

    for user_injury in user_injuries:
        db.session.delete(user_injury)

    session.pop("delete_code", None)
    session.pop("delete_code_email", None)

    db.session.delete(user)
    db.session.commit()

    logout_user()

    return jsonify({"status": "deleted"})


