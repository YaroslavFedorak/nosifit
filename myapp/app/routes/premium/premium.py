from flask import Blueprint, render_template, redirect
from myapp.app import db
from flask_login import login_required, current_user

premium_bp = Blueprint("premium", __name__)

@premium_bp.route("/premium")
@login_required
def premium_page():
    user = current_user
    return render_template("app/premium.html", user=user)

@premium_bp.route("/premium/activate")
@login_required
def activate_premium():
    user = current_user
    user.is_premium = True
    db.session.commit()
    return redirect("/premium")
