from flask import Blueprint, render_template
from flask_login import current_user

public_bp = Blueprint("public", __name__, url_prefix="")


def get_base():
    return (
        "app/base_app.html"
        if current_user.is_authenticated
        else "public/base_public.html"
    )


@public_bp.route("/about")
def about():
    return render_template("public/about.html", base_template=get_base())


@public_bp.route("/pricing")
def pricing():
    return render_template("public/pricing.html", base_template=get_base())


@public_bp.route("/demo")
def demo():
    return render_template("public/demo.html", base_template=get_base())
