import mimetypes
import os

from dotenv import load_dotenv
from flask import Flask, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix

from backend.app.extensions import db, login_manager, migrate, mail, oauth
from web.app.i18n import init_i18n
from web.app.security import init_security

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(BASE_DIR, ".env"))


# The barcode scanner's WebAssembly decoder must be served as application/wasm.
mimetypes.add_type("application/wasm", ".wasm")


def create_app(config=None):
    app = Flask(__name__)
    app.config.from_object("backend.config.Config")

    init_i18n(app)

    if config:
        app.config.update(config)

    init_security(app)

    if app.config.get("IS_PRODUCTION") and not app.config.get("TESTING"):
        if not app.config.get("SECRET_KEY") or len(app.config["SECRET_KEY"]) < 32:
            raise RuntimeError(
                "SECRET_KEY must be set to a long random value in production "
                "(python -c \"import secrets; print(secrets.token_hex(32))\")"
            )
        if not app.config.get("SQLALCHEMY_DATABASE_URI"):
            raise RuntimeError("DATABASE_URL is not set")

    # Behind Railway's proxy the app itself sees plain HTTP. Trust the
    # X-Forwarded-* headers so url_for(..., _external=True) builds https://
    # links (OAuth callbacks, password reset emails) with the real host.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    @app.get("/healthz")
    def healthz():
        return jsonify({"status": "ok"})

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    oauth.init_app(app)

    login_manager.login_view = "auth.login"

    from backend.app.models.user import User
    from backend.app.models.verification_code import VerificationCode
    from backend.app.models.oauth_account import OAuthAccount
    from backend.app.models.telegram import TelegramIdentity, TelegramLinkToken
    from backend.app.models.recovery.habit import RecoveryHabit
    from backend.app.models.recovery.user_habit import UserRecoveryHabit
    from backend.app.models.recovery.habit_log import RecoveryHabitLog

    from backend.app.utils.session_auth import fingerprint_matches, parse_session_id

    @login_manager.user_loader
    def load_user(session_id):
        parsed = parse_session_id(session_id)
        if parsed is None:  # old integer-only ids: log in again
            return None
        user_id, fingerprint = parsed
        user = db.session.get(User, user_id)
        if user is None or not fingerprint_matches(user, fingerprint):
            return None
        return user

    # Telegram sessions: limited to the bot's API, revoked with the identity.
    from web.app.routes.auth.telegram_session import enforce_telegram_session

    app.before_request(enforce_telegram_session)

    oauth.register(
        name="google",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

    oauth.register(
        name="github",
        client_id=os.getenv("GITHUB_CLIENT_ID"),
        client_secret=os.getenv("GITHUB_CLIENT_SECRET"),
        access_token_url="https://github.com/login/oauth/access_token",
        authorize_url="https://github.com/login/oauth/authorize",
        api_base_url="https://api.github.com/",
        client_kwargs={"scope": "user:email"},
    )

    from web.app.routes import (
        auth_bp,
        google_bp,
        github_bp,
        email_verification_bp,
        complete_profile_bp,
        telegram_api_bp,
        telegram_link_bp,
        root_bp,
        public_bp,
        info_bp,
        i18n_bp,
        dashboard_bp,
        dashboard_api_bp,
        training_dashboard_api_bp,
        training_pages_bp,
        training_explanation_bp,
        training_api_bp,
        nutrition_pages_bp,
        nutrition_api,
        recovery_pages_bp,
        recovery_bp,
        assessment_pages_bp,
        assessment_bp,
        equipment_pages_bp,
        equipment_api,
        training_plan_pages_bp,
        plan_bp,
        premium_bp,
        profile_pages_bp,
        profile_view_bp,
        profile_update_bp,
        password_change_bp,
        email_change_bp,
        delete_request_bp,
        delete_confirm_bp,
        delete_final_bp,
        oauth_disconnect_bp,
        connected_accounts_bp,
        questionnaire_pages_bp,
        questionnaire_bp,
        tracker_pages_bp,
        onboarding_api,
        injury_api,
    )

    app.register_blueprint(auth_bp)
    app.register_blueprint(google_bp)
    app.register_blueprint(github_bp)
    app.register_blueprint(email_verification_bp)
    app.register_blueprint(complete_profile_bp)
    app.register_blueprint(telegram_api_bp)
    app.register_blueprint(telegram_link_bp)

    app.register_blueprint(root_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(info_bp)
    app.register_blueprint(i18n_bp)

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(dashboard_api_bp)
    app.register_blueprint(training_dashboard_api_bp)

    app.register_blueprint(training_pages_bp)
    app.register_blueprint(training_explanation_bp)
    app.register_blueprint(training_api_bp)

    app.register_blueprint(nutrition_pages_bp)
    app.register_blueprint(nutrition_api)

    app.register_blueprint(recovery_pages_bp)
    app.register_blueprint(recovery_bp)

    app.register_blueprint(assessment_pages_bp)
    app.register_blueprint(assessment_bp)

    app.register_blueprint(equipment_pages_bp)
    app.register_blueprint(equipment_api)

    app.register_blueprint(training_plan_pages_bp)
    app.register_blueprint(plan_bp)

    app.register_blueprint(premium_bp)

    app.register_blueprint(profile_pages_bp)
    app.register_blueprint(profile_view_bp)
    app.register_blueprint(profile_update_bp)
    app.register_blueprint(password_change_bp)
    app.register_blueprint(email_change_bp)
    app.register_blueprint(delete_request_bp)
    app.register_blueprint(delete_confirm_bp)
    app.register_blueprint(delete_final_bp)
    app.register_blueprint(oauth_disconnect_bp)
    app.register_blueprint(connected_accounts_bp)

    app.register_blueprint(questionnaire_pages_bp)
    app.register_blueprint(questionnaire_bp)

    app.register_blueprint(tracker_pages_bp)

    app.register_blueprint(onboarding_api)
    app.register_blueprint(injury_api)

    return app
