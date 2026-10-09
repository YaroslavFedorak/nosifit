from datetime import date

from flask import Blueprint, current_app, g, render_template

from backend.app.services.telegram_auth import clean_bot_username
from web.app.i18n.locale import DEFAULT_LOCALE, load_translation

root_bp = Blueprint("root", __name__, url_prefix="")

@root_bp.route("/")
def landing():
    # One load per request: the page reads ~150 keys, and public_t()
    # re-reads the JSON files for every key.
    copy = load_translation(getattr(g, "locale", DEFAULT_LOCALE), "public")

    return render_template(
        "public/landing.html",
        L=copy.get("landing", {}),
        telegram_bot=clean_bot_username(current_app.config.get("TELEGRAM_BOT_USERNAME")),
        current_year=date.today().year,
    )
