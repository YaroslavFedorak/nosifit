import os
from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_mail import Mail
from authlib.integrations.flask_client import OAuth

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(BASE_DIR, ".env"))

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
mail = Mail()
oauth = OAuth()


def create_app():
    app = Flask(__name__)
    app.config.from_object("myapp.app.config.Config")

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    oauth.init_app(app)

    login_manager.login_view = "auth.login"

    from myapp.app.models.user import User
    from myapp.app.models.verification_code import VerificationCode
    from myapp.app.models.oauth_account import OAuthAccount
    from myapp.app.models.recovery.habit import RecoveryHabit
    from myapp.app.models.recovery.user_habit import UserRecoveryHabit
    from myapp.app.models.recovery.habit_log import RecoveryHabitLog

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

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

    from myapp.app.routes.auth.oauth_google import google_bp
    from myapp.app.routes.auth.oauth_github import github_bp
    from myapp.app.routes.auth.email_verification import email_verification_bp
    from myapp.app.routes.auth.complete_profile import complete_profile_bp
    from myapp.app.routes.auth_main import auth_bp

    from myapp.app.routes.root import root_bp
    from myapp.app.routes.public import public_bp
    from myapp.app.routes.public_info import info_bp

    from myapp.app.routes.dashboard import dashboard_page_bp, dashboard_api_bp
    from myapp.app.routes.dashboard_pages import dashboard_pages_bp

    from myapp.app.routes.plan import plan_bp
    from myapp.app.routes.assessment import assessment_bp
    from myapp.app.routes.equipment import equipment_bp
    from myapp.app.routes.questionnaire import questionnaire_bp

    from myapp.app.routes.nutrition.nutrition_api import nutrition_api
    from myapp.app.routes.premium import premium_bp

    from myapp.app.routes.profile.profile_view import profile_view_bp
    from myapp.app.routes.profile.profile_update import profile_update_bp
    from myapp.app.routes.profile.password_change import password_change_bp
    from myapp.app.routes.profile.email_change import email_change_bp
    from myapp.app.routes.profile.delete_account_request import delete_request_bp
    from myapp.app.routes.profile.delete_account_confirm import delete_confirm_bp
    from myapp.app.routes.profile.delete_account_final import delete_final_bp
    from myapp.app.routes.profile.oauth_disconnect import oauth_disconnect_bp

    from myapp.app.routes.training.api_training import bp as training_api_bp
    from myapp.app.routes.onboarding_api import onboarding_api
    from myapp.app.routes.equipment_api import equipment_api
    from myapp.app.routes.injury_api import injury_api

    from myapp.app.routes.recovery.recovery_api import recovery_bp

    app.register_blueprint(google_bp)
    app.register_blueprint(github_bp)
    app.register_blueprint(email_verification_bp)
    app.register_blueprint(complete_profile_bp)
    app.register_blueprint(auth_bp)

    app.register_blueprint(root_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(info_bp)

    app.register_blueprint(dashboard_page_bp)
    app.register_blueprint(dashboard_api_bp)
    app.register_blueprint(dashboard_pages_bp)

    app.register_blueprint(plan_bp)
    app.register_blueprint(assessment_bp)
    app.register_blueprint(equipment_bp)
    app.register_blueprint(questionnaire_bp)

    app.register_blueprint(nutrition_api)
    app.register_blueprint(premium_bp)

    app.register_blueprint(profile_view_bp)
    app.register_blueprint(profile_update_bp)
    app.register_blueprint(password_change_bp)
    app.register_blueprint(email_change_bp)
    app.register_blueprint(delete_request_bp)
    app.register_blueprint(delete_confirm_bp)
    app.register_blueprint(delete_final_bp)
    app.register_blueprint(oauth_disconnect_bp)

    app.register_blueprint(training_api_bp)
    app.register_blueprint(onboarding_api)
    app.register_blueprint(equipment_api)
    app.register_blueprint(injury_api)

    app.register_blueprint(recovery_bp)

    return app
