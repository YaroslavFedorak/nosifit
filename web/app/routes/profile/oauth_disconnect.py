from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from backend.app.extensions import db
from backend.app.models.oauth_account import OAuthAccount
from backend.app.services.telegram_auth import (
    OAUTH_PROVIDERS,
    lock_user,
    remaining_methods_without,
)

oauth_disconnect_bp = Blueprint("oauth_disconnect", __name__)


@oauth_disconnect_bp.post("/profile/oauth_disconnect")
@login_required
def oauth_disconnect():
    provider = request.form.get("provider")
    if provider not in OAUTH_PROVIDERS:
        return jsonify({"error": "Not connected"}), 404

    # The row lock serialises concurrent disconnects (Google, GitHub,
    # Telegram), so they cannot together remove every way to sign in.
    user = lock_user(current_user.id)

    acc = OAuthAccount.query.filter_by(
        provider=provider, user_id=current_user.id
    ).first()

    if not acc or user is None:
        db.session.rollback()
        return jsonify({"error": "Not connected"}), 404

    if remaining_methods_without(user, provider) == 0:
        db.session.rollback()
        return jsonify({"error": "last_method"}), 400

    db.session.delete(acc)
    db.session.commit()

    return jsonify({"message": "OAuth disconnected"}), 200
