import mimetypes
import os

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_compress import Compress
from werkzeug.middleware.proxy_fix import ProxyFix

from backend.app.extensions import db, login_manager, migrate, mail, oauth
from web.app.assets import compute_asset_version, init_assets
from web.app.i18n import init_i18n
from web.app.security import init_security

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(BASE_DIR, ".env"))


# The barcode scanner's WebAssembly decoder must be served as application/wasm.
mimetypes.add_type("application/wasm", ".wasm")

ASSET_VERSION = compute_asset_version()

compress = Compress()


def create_app(config=None, *, pages=True):
    """The NosiFit app. ``pages=False`` builds the JSON API alone: no pages,
    no sign-in forms. Production runs both together; the API-only app is how
    the tests check that the API could run as its own service."""
    app = Flask(__name__, static_url_path=f"/static/{ASSET_VERSION}")
    app.config.from_object("backend.config.Config")
    app.config.setdefault(
        "COMPRESS_MIMETYPES",
        [
            "text/html",
            "text/css",
            "text/javascript",
            "application/javascript",
            "application/json",
            "application/manifest+json",
            "application/wasm",
            "image/svg+xml",
        ],
    )
    app.config.setdefault(
        "COMPRESS_STREAMING_ENDPOINT_CONDITIONAL", ["static", "static_unversioned"]
    )

    init_i18n(app)

    if config:
        app.config.update(config)

    init_security(app)
    init_assets(app, ASSET_VERSION)
    compress.init_app(app)

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
    from auth.telegram_session import enforce_telegram_session

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

    # Pages and their form posts belong to web; everything under /api/ to
    # the api package (docs/architecture.md).
    from api import register_api

    if pages:
        from web.app.routes import register_pages

        register_pages(app)
    register_api(app)

    return app
