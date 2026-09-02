from flask import Blueprint, session, jsonify

delete_confirm_bp = Blueprint("delete_confirm", __name__)

@delete_confirm_bp.route("/profile/delete/confirm", methods=["POST"])
def confirm_delete():
    from flask import request

    code = request.json.get("code")

    if "delete_code" not in session:
        return jsonify({"status": "expired"}), 400

    if str(code) != str(session["delete_code"]):
        return jsonify({"status": "wrong"}), 400

    return jsonify({"status": "ok"})