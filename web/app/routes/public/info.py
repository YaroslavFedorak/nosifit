from flask import Blueprint, render_template
from flask_login import current_user

info_bp = Blueprint("info", __name__)


def get_base():
    return (
        "app/base_app.html"
        if current_user.is_authenticated
        else "public/base_public.html"
    )


@info_bp.route("/info")
def info_page():
    return render_template("public/info.html", active="info", base_template=get_base())
