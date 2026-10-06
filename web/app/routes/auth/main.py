from flask import Blueprint, render_template, request, redirect, flash, session, url_for
from flask_login import login_user, logout_user
from sqlalchemy.exc import IntegrityError
from backend.app.extensions import db
from backend.app.models.user import User
from backend.app.models.user_profile import UserProfile
from backend.app.utils.email_service import send_password_reset_email
from backend.app.utils.mailer import EmailSendError
from backend.app.utils.token import verify_reset_token
from backend.app.utils.validation import (
    ValidationError,
    clean_choice,
    parse_profile_number,
    password_problem,
)
from web.app.security import client_ip, hit_limit, reset_limit, too_many_requests

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

# Per email: slows down guessing one account's password.
LOGIN_LIMIT_PER_EMAIL = (10, 15 * 60)
# Per IP: slows down credential stuffing across many accounts. The Telegram
# bot logs in from one IP for all its users, so this stays generous.
LOGIN_LIMIT_PER_IP = (50, 5 * 60)
RESET_LIMIT_PER_EMAIL = (3, 60 * 60)
RESET_LIMIT_PER_IP = (10, 60 * 60)

LOGIN_FAILED_MESSAGE = "Невірна електронна пошта або пароль"


def start_user_session(user):
    """Log ``user`` in on a fresh session (no data carried over from before)."""
    session.clear()
    login_user(user, remember=True)


@auth_bp.route("/login", methods=["GET", "POST"], endpoint="login")
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if hit_limit("login-ip", client_ip(), *LOGIN_LIMIT_PER_IP) or hit_limit(
            "login-email", email, *LOGIN_LIMIT_PER_EMAIL
        ):
            flash("Забагато спроб входу. Спробуйте пізніше.", "error")
            return redirect(url_for("auth.login"))

        user = User.query.filter(db.func.lower(User.email) == email).first()

        # Same answer for "no such user" and "wrong password": the login form
        # must not tell an attacker which emails are registered.
        if not user or not user.check_password(password):
            flash(LOGIN_FAILED_MESSAGE, "error")
            return redirect(url_for("auth.login"))

        reset_limit("login-email", email)

        if not user.profile:
            profile = UserProfile(
                user_id=user.id,
                training_location="home",
                onboarding_completed=False,
            )
            db.session.add(profile)
            db.session.commit()

        start_user_session(user)
        return redirect(url_for("dashboard.dashboard"))

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET"], endpoint="register")
def register():
    return render_template("auth/register.html")


def _profile_from_registration(reg_data):
    """Validated profile fields from the registration form, or ValidationError."""
    return {
        "weight": parse_profile_number("weight", reg_data.get("weight")),
        "height": parse_profile_number("height", reg_data.get("height")),
        "age": parse_profile_number("age", reg_data.get("age")),
        "workouts_per_week": parse_profile_number(
            "workouts_per_week", reg_data.get("workouts_per_week")
        ),
        "gender": clean_choice("gender", reg_data.get("gender")),
        "activity": clean_choice("activity", reg_data.get("activity")),
        "goal": clean_choice("goal", reg_data.get("goal")),
        "experience": clean_choice("experience", reg_data.get("experience")),
        "training_location": clean_choice(
            "training_location", reg_data.get("training_location")
        )
        or "home",
    }


@auth_bp.route(
    "/register_complete",
    methods=["GET", "POST"],
    endpoint="register_complete",
)
def register_complete():
    reg_data = session.get("reg_data")
    verified_email = session.get("verified_email")

    if (
        not reg_data
        or not verified_email
        or reg_data.get("email") != verified_email
        or not reg_data.get("password_hash")
    ):
        flash("Спочатку підтвердіть email", "error")
        return redirect(url_for("auth.register"))

    if request.method == "POST":
        if User.query.filter(db.func.lower(User.email) == verified_email).first():
            session.pop("reg_data", None)
            session.pop("verified_email", None)
            flash("Ця пошта вже зареєстрована. Увійдіть у свій акаунт.", "error")
            return redirect(url_for("auth.login"))

        try:
            profile_fields = _profile_from_registration(reg_data)
        except ValidationError:
            flash("Перевірте дані профілю.", "error")
            return redirect(url_for("auth.register"))

        user = User(
            username=reg_data["username"],
            email=verified_email,
            # Hashed in /verify/send_code; the plain password never reaches the session.
            password=reg_data["password_hash"],
        )

        db.session.add(user)
        try:
            db.session.flush()
        except IntegrityError:  # registered concurrently
            db.session.rollback()
            flash("Ця пошта вже зареєстрована. Увійдіть у свій акаунт.", "error")
            return redirect(url_for("auth.login"))

        profile = UserProfile(
            user_id=user.id,
            wants_nutrition=True,
            wants_recovery=False,
            onboarding_completed=False,
            **profile_fields,
        )

        db.session.add(profile)
        db.session.commit()

        start_user_session(user)

        return redirect(url_for("dashboard.dashboard"))

    return render_template("auth/register_complete.html")


@auth_bp.route("/logout", methods=["GET", "POST"], endpoint="logout")
def logout():
    logout_user()
    session.clear()
    return redirect(url_for("root.landing"))


@auth_bp.route(
    "/reset",
    methods=["GET", "POST"],
    endpoint="reset_password",
)
def reset_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        if hit_limit("reset-ip", client_ip(), *RESET_LIMIT_PER_IP):
            return too_many_requests("Забагато запитів. Спробуйте пізніше.")

        # Over the per-email limit the page looks the same as a sent email,
        # so the limit reveals nothing about the account.
        user = None
        if email and not hit_limit("reset-email", email, *RESET_LIMIT_PER_EMAIL):
            user = User.query.filter(db.func.lower(User.email) == email).first()

        if user:
            try:
                send_password_reset_email(user)
            except EmailSendError:
                flash("Не вдалося надіслати лист. Спробуйте трохи пізніше.", "error")
                return render_template("auth/reset_password.html")

        return render_template(
            "auth/reset_status.html",
            mode="sent",
            email=email,
        )

    return render_template("auth/reset_password.html")


@auth_bp.route(
    "/reset/<token>",
    methods=["GET", "POST"],
    endpoint="reset_with_token",
)
def reset_with_token(token):
    # The token is bound to the current password hash, so it stops working
    # as soon as it has been used once (or the password changed otherwise).
    user = verify_reset_token(token)

    if user is None:
        flash("Посилання недійсне або прострочене.", "error")
        return redirect(url_for("auth.reset_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if not password or not confirm:
            flash("Заповніть обидва поля пароля.", "error")
            return redirect(request.url)

        if password != confirm:
            flash("Паролі не співпадають.", "error")
            return redirect(request.url)

        problem = password_problem(password)
        if problem:
            flash(problem, "error")
            return redirect(request.url)

        user.set_password(password)
        db.session.commit()

        start_user_session(user)

        return redirect(url_for("dashboard.dashboard"))

    return render_template("auth/new_password.html")


@auth_bp.route("/forgot", endpoint="forgot")
def forgot_alias():
    return redirect(url_for("auth.reset_password"))
