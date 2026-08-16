from flask import Blueprint, render_template

root_bp = Blueprint("root", __name__, url_prefix="")

@root_bp.route("/")
def landing():
    return render_template("public/landing.html")
