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

    from myapp.app.routes import (
        auth_bp,
        google_bp,
        github_bp,
        email_verification_bp,
        complete_profile_bp,
        root_bp,
        public_bp,
        info_bp,
        dashboard_bp,
        dashboard_api_bp,
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

    app.register_blueprint(root_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(info_bp)

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(dashboard_api_bp)

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

    app.register_blueprint(questionnaire_pages_bp)
    app.register_blueprint(questionnaire_bp)

    app.register_blueprint(tracker_pages_bp)

    app.register_blueprint(onboarding_api)
    app.register_blueprint(injury_api)

    return app
