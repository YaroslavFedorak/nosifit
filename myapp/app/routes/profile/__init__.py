from .pages import profile_pages_bp
from .profile_view import profile_view_bp
from .profile_update import profile_update_bp
from .password_change import password_change_bp
from .email_change import email_change_bp
from .delete_account_request import delete_request_bp
from .delete_account_confirm import delete_confirm_bp
from .delete_account_final import delete_final_bp
from .oauth_disconnect import oauth_disconnect_bp

__all__ = [
    "profile_pages_bp",
    "profile_view_bp",
    "profile_update_bp",
    "password_change_bp",
    "email_change_bp",
    "delete_request_bp",
    "delete_confirm_bp",
    "delete_final_bp",
    "oauth_disconnect_bp",
]
