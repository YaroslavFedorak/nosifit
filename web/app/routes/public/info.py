from flask import Blueprint, render_template, request
from flask_login import current_user

info_bp = Blueprint("info", __name__)


@info_bp.route("/info")
def info_page():
    use_app_layout = (
        current_user.is_authenticated and request.args.get("layout") == "app"
    )

    return render_template(
        "public/info.html",
        base_template="app/base_app.html" if use_app_layout else "public/base_public.html",
        active="info",
        layout_mode="app" if use_app_layout else "public",
    )
