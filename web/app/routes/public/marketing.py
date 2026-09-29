from flask import Blueprint, render_template

public_bp = Blueprint("public", __name__)


def get_base():
    return "public/base_public.html"


@public_bp.route("/about")
def about():
    return render_template("public/about.html", base_template=get_base())


@public_bp.route("/contact")
def contact():
    return render_template("public/contact.html", base_template=get_base())


@public_bp.route("/pricing")
def pricing():
    return render_template("public/pricing.html", base_template=get_base())


@public_bp.route("/demo")
def demo():
    return render_template("public/demo.html", base_template=get_base())
