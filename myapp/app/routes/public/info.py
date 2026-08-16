from flask import Blueprint, render_template
from flask_login import current_user

info_bp = Blueprint("info", __name__)


@info_bp.route("/info")
def info_page():
    return render_template("public/info.html", active="info")
