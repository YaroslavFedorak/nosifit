from .auth.main import auth_bp
from .public.root import root_bp

from .public.marketing import public_bp
from .public.info import info_bp

from .auth.oauth_google import google_bp
from .auth.oauth_github import github_bp
from .auth.email_verification import email_verification_bp
from .auth.complete_profile import complete_profile_bp

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
from .equipment.api import equipment_api

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

from .questionnaire.pages import questionnaire_pages_bp
from .questionnaire.questionnaire import questionnaire_bp

from .tracker.pages import tracker_pages_bp

from .onboarding.api import onboarding_api
from .injury.api import injury_api

from .dashboard import training_dashboard_api_bp
