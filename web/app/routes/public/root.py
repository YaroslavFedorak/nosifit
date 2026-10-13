from datetime import date

from flask import Blueprint, current_app, g, redirect, render_template, request, url_for
from flask_login import current_user

from backend.app.services.telegram_auth import clean_bot_username
from web.app.i18n.locale import DEFAULT_LOCALE, load_translation

root_bp = Blueprint("root", __name__, url_prefix="")

# Marks a link to the landing from inside the site (the logo, "Home"), which
# shows the landing even to a signed-in user.
HOME_PARAM = "home"


@root_bp.app_context_processor
def _landing_url():
    def landing_url():
        if current_user.is_authenticated:
            return url_for("root.landing", **{HOME_PARAM: 1})
        return url_for("root.landing")

    return {"landing_url": landing_url}


@root_bp.route("/")
def landing():
    # Opening the site while signed in (also from a "remember me" cookie):
    # straight to the app. The logo and "Home" links still show the landing.
    if current_user.is_authenticated and HOME_PARAM not in request.args:
        return redirect(url_for("dashboard.dashboard"))

    # One load per request: the page reads ~150 keys, and public_t()
    # re-reads the JSON files for every key.
    copy = load_translation(getattr(g, "locale", DEFAULT_LOCALE), "public")

    return render_template(
        "public/landing.html",
        L=copy.get("landing", {}),
        telegram_bot=clean_bot_username(current_app.config.get("TELEGRAM_BOT_USERNAME")),
        current_year=date.today().year,
    )
