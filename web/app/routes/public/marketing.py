from flask import Blueprint, render_template, request
from flask_login import current_user

public_bp = Blueprint("public", __name__)


def get_base():
    if current_user.is_authenticated and request.args.get("layout") == "app":
        return "app/base_app.html"
    return "public/base_public.html"


@public_bp.route("/about")
def about():
    return render_template(
        "public/about.html",
        base_template=get_base(),
        active="about",
    )


@public_bp.route("/pricing")
def pricing():
    return render_template("public/pricing.html", base_template=get_base())


@public_bp.route("/demo")
def demo():
    return render_template("public/demo.html", base_template=get_base())
