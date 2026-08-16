from flask import Blueprint, render_template, request, redirect, flash, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user
from myapp.app import db
from myapp.app.models.user import User
from myapp.app.models.user_profile import UserProfile
from myapp.app.utils.email_service import send_password_reset_email
from myapp.app.utils.token import verify_reset_token

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
print("LOADED AUTH_MAIN:", __file__)


@auth_bp.route("/login", methods=["GET", "POST"], endpoint="login")
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()

        if not user:
            flash("Користувача не знайдено", "error")
            return redirect(url_for("auth.login"))

        if not check_password_hash(user.password, password):
            flash("Невірний пароль", "error")
            return redirect(url_for("auth.login"))

        if not user.profile:
            profile = UserProfile(
                user_id=user.id, training_location="home", onboarding_completed=False
            )
            db.session.add(profile)
            db.session.commit()

        login_user(user, remember=True)
        return redirect(url_for("dashboard_pages.dashboard"))

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET"], endpoint="register")
def register():
    return render_template("auth/register.html")


@auth_bp.route(
    "/register_complete", methods=["GET", "POST"], endpoint="register_complete"
)
def register_complete():
    reg_data = session.get("reg_data")
    verified_email = session.get("verified_email")

    if not reg_data or not verified_email:
        flash("Спочатку підтвердіть email", "error")
        return redirect(url_for("auth.register"))

    if request.method == "POST":
        hashed_password = generate_password_hash(reg_data["password"])

        user = User(
            username=reg_data["username"],
            email=verified_email,
            password=hashed_password,
        )

        db.session.add(user)
        db.session.commit()

        profile = UserProfile(
            user_id=user.id,
            training_location=reg_data.get("training_location", "home"),
            wants_nutrition=True,
            wants_recovery=False,
            onboarding_completed=False,
            weight=float(reg_data.get("weight", 0)) if reg_data.get("weight") else None,
            height=float(reg_data.get("height", 0)) if reg_data.get("height") else None,
            age=int(reg_data.get("age", 0)) if reg_data.get("age") else None,
            gender=reg_data.get("gender"),
            activity=reg_data.get("activity"),
            goal=reg_data.get("goal"),
            experience=reg_data.get("experience"),
            workouts_per_week=(
                int(reg_data.get("workouts_per_week", 0))
                if reg_data.get("workouts_per_week")
                else None
            ),
        )

        db.session.add(profile)
        db.session.commit()

        session.pop("reg_data", None)
        session.pop("verified_email", None)

        login_user(user, remember=True)
        return redirect(url_for("dashboard_pages.dashboard"))

    return render_template("auth/register_complete.html")


@auth_bp.route("/logout", endpoint="logout")
def logout():
    logout_user()
    return redirect(url_for("root.landing"))


@auth_bp.route("/reset", methods=["GET", "POST"], endpoint="reset_password")
def reset_password():
    if request.method == "POST":
        email = request.form.get("email")
        user = User.query.filter_by(email=email).first()

        if user:
            send_password_reset_email(user)

        return render_template("auth/reset_status.html", mode="sent", email=email)

    return render_template("auth/reset_password.html")


@auth_bp.route("/reset/<token>", methods=["GET", "POST"], endpoint="reset_with_token")
def reset_with_token(token):
    email = verify_reset_token(token)
    if isinstance(email, bytes):
        email = email.decode("utf-8")
    email = email.strip().lower()

    if not email:
        flash("Посилання недійсне або прострочене.", "error")
        return redirect(url_for("auth.reset_password"))

    if request.method == "POST":
        password = request.form.get("password")
        confirm = request.form.get("confirm")

        if password != confirm:
            flash("Паролі не співпадають.", "error")
            return redirect(request.url)

        user = User.query.filter(db.func.lower(User.email) == email).first()
        user.password = generate_password_hash(password)
        db.session.commit()

        login_user(user, remember=True)
        return redirect(url_for("dashboard_pages.dashboard"))

    return render_template("auth/new_password.html")


@auth_bp.route("/forgot", endpoint="forgot")
def forgot_alias():
    return redirect(url_for("auth.reset_password"))
