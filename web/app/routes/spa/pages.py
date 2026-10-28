"""The React interface (see frontend/), served under /app.

The classic pages are untouched. This blueprint only renders the HTML shell:
the page's language, the signed-in user and the built bundle. Everything
else the interface needs it fetches from the JSON API with the same session.
"""

import os

from flask import Blueprint, abort, current_app, g, redirect, render_template, url_for
from flask_login import current_user

spa_pages_bp = Blueprint("spa_pages", __name__, url_prefix="/app")

# Pages anyone may open; the others need a signed-in user.
PUBLIC_PAGES = frozenset({"welcome", "how-it-works"})
USER_PAGES = frozenset({"dashboard", "training", "nutrition", "recovery"})

BUNDLE = os.path.join("app", "assets", "app.js")


def _bundle_is_built() -> bool:
    return os.path.isfile(os.path.join(current_app.static_folder, BUNDLE))


@spa_pages_bp.get("/", defaults={"page": ""})
@spa_pages_bp.get("/<path:page>")
def shell(page):
    name = page.strip("/")

    if not name:
        landing = "dashboard" if current_user.is_authenticated else "welcome"
        return redirect(url_for("spa_pages.shell", page=landing))

    if name not in PUBLIC_PAGES | USER_PAGES:
        abort(404)

    if name in USER_PAGES and not current_user.is_authenticated:
        return current_app.login_manager.unauthorized()

    if not _bundle_is_built():
        abort(503, description="The interface is not built: run `npm --prefix frontend run build`.")

    user = None
    if current_user.is_authenticated:
        user = {"id": current_user.id, "name": current_user.username}

    return render_template(
        "app/spa.html",
        locale=g.locale,
        bootstrap={"locale": g.locale, "user": user},
    )
