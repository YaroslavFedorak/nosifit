from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from web.app import db
from web.app.models.oauth_account import OAuthAccount

oauth_disconnect_bp = Blueprint("oauth_disconnect", __name__)


@oauth_disconnect_bp.post("/profile/oauth_disconnect")
@login_required
def oauth_disconnect():
    provider = request.form.get("provider")

    acc = OAuthAccount.query.filter_by(
        provider=provider, user_id=current_user.id
    ).first()

    if not acc:
        return jsonify({"error": "Not connected"}), 404

    db.session.delete(acc)
    db.session.commit()

    return jsonify({"message": "OAuth disconnected"}), 200
