"""Private admin analytics: the page and its JSON data.

Both endpoints check the administrator on the backend (ADMIN_EMAILS, see
backend/app/utils/admin.py). Anyone else, including Telegram sessions, gets
a plain 404, so the existence of the page is not revealed; a visitor who is
not signed in is sent to the sign-in form (page) or gets 401 (data).
"""

from functools import wraps

from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, url_for
from flask_login import current_user

from auth.telegram_session import is_telegram_session
from backend.app.services.analytics import RANGES, build_analytics
from backend.app.utils.admin import is_admin

admin_analytics_bp = Blueprint("admin_analytics", __name__, url_prefix="/admin")


def _no_store(response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.path.endswith("/data"):
                return _no_store(jsonify({"error": "unauthorized"})), 401
            return redirect(url_for("auth.login"))
        if is_telegram_session() or not is_admin(
            current_user, current_app.config.get("ADMIN_EMAILS")
        ):
            abort(404)
        return view(*args, **kwargs)

    return wrapped


@admin_analytics_bp.get("/analytics")
@admin_required
def analytics_page():
    response = current_app.make_response(
        render_template("app/admin/analytics.html", ranges=list(RANGES))
    )
    return _no_store(response)


@admin_analytics_bp.get("/analytics/data")
@admin_required
def analytics_data():
    range_key = request.args.get("range", "30")
    if range_key not in RANGES:
        return _no_store(jsonify({"error": "invalid_range", "allowed": list(RANGES)})), 400
    return _no_store(jsonify(build_analytics(range_key)))
