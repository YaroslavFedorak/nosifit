from .auth.main import auth_bp
from .public.root import root_bp

from .public.marketing import public_bp
from .public.info import info_bp

from .auth.oauth_google import google_bp
from .auth.oauth_github import github_bp
from .auth.email_verification import email_verification_bp
from .auth.complete_profile import complete_profile_bp
from .auth.telegram_api import telegram_api_bp
from .auth.telegram_link import telegram_link_bp

from .dashboard.page import dashboard_bp
from .dashboard.api import dashboard_api_bp

from .training.pages import training_pages_bp
from .training.pages_explanation import training_explanation_bp
from .training.api_training import training_api_bp

from .nutrition.pages import nutrition_pages_bp
from .nutrition.nutrition_api import nutrition_api

from .recovery.pages import recovery_pages_bp
from .recovery.recovery_api import recovery_bp

from .assessment.pages import assessment_pages_bp
from .assessment.assessment import assessment_bp

from .equipment.pages import equipment_pages_bp

from .training_plan.pages import training_plan_pages_bp
from .training_plan.plan import plan_bp

from .premium.premium import premium_bp

from .profile.pages import profile_pages_bp
from .profile.profile_view import profile_view_bp
from .profile.profile_update import profile_update_bp
from .profile.password_change import password_change_bp
from .profile.email_change import email_change_bp
from .profile.delete_account_request import delete_request_bp
from .profile.delete_account_confirm import delete_confirm_bp
from .profile.delete_account_final import delete_final_bp
from .profile.oauth_disconnect import oauth_disconnect_bp
from .profile.connected_accounts import connected_accounts_bp

from .questionnaire.pages import questionnaire_pages_bp
from .questionnaire.questionnaire import questionnaire_bp

from .tracker.pages import tracker_pages_bp

from .dashboard import training_dashboard_api_bp


# Registration order matters only for rules registered twice ("/" and
# "/assessment/"): the first blueprint wins. Keep it as it is.
PAGE_BLUEPRINTS = (
    auth_bp,
    google_bp,
    github_bp,
    email_verification_bp,
    complete_profile_bp,
    telegram_link_bp,
    root_bp,
    public_bp,
    info_bp,
    dashboard_bp,
    training_pages_bp,
    training_explanation_bp,
    nutrition_pages_bp,
    recovery_pages_bp,
    assessment_pages_bp,
    assessment_bp,
    equipment_pages_bp,
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
)


def register_pages(app):
    for blueprint in PAGE_BLUEPRINTS:
        app.register_blueprint(blueprint)
