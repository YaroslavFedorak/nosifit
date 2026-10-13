from flask import Blueprint, request, render_template, redirect, session, flash, url_for
from backend.app.models.verification_code import VerificationCode
from backend.app.models.user import User
import secrets

from werkzeug.security import generate_password_hash

from backend.app.extensions import db
from backend.app.utils.mailer import EmailSendError, send_email
from backend.app.utils.validation import clean_username, normalize_email, password_problem
from web.app.security import client_ip, hit_limit, reset_limit, too_many_requests

from backend.app.services.verification_codes import (
    MAX_CODE_ATTEMPTS,
    SEND_LIMIT_PER_EMAIL,
    VERIFY_ATTEMPT_WINDOW,
    code_is_expired,
    issue_code,
    new_code,
)

# The code store, its expiry and the per-address limits are in core
# (backend/app/services/verification_codes.py), shared with the Telegram
# registration. The per-client limit needs the request and stays here.
SEND_LIMIT_PER_IP = (20, 60 * 60)

# Registration form fields kept until the email is verified. Anything else in
# the form (and the plain-text password) never goes into the session.
REG_PROFILE_FIELDS = (
    "gender",
    "age",
    "height",
    "weight",
    "activity",
    "goal",
    "experience",
    "workouts_per_week",
    "training_location",
)

email_verification_bp = Blueprint("email_verification", __name__, url_prefix="/verify")


_new_code = new_code
_is_expired = code_is_expired


def send_verification_email(email, code):
    send_email(
        to=email,
        subject="Код для реєстрації в NosiFit",
        text=(
            f"Привіт!\n\n"
            f"Ваш код для реєстрації в NosiFit:\n\n"
            f"{code}\n\n"
            f"Код діє 10 хвилин.\n"
            f"Якщо ви не реєструвались у NosiFit, просто не зважайте на цей лист.\n\n"
            f"Команда NosiFit"
        ),
        html=f"""
    <p>Привіт!</p>
    <p>Ваш код для реєстрації в <b>NosiFit</b>:</p>
    <h1 style="font-size: 32px; letter-spacing: 4px;">{code}</h1>
    <p>Код діє 10 хвилин. Якщо ви не реєструвались у NosiFit, просто не зважайте на цей лист.</p>
    """,
    )


def send_existing_account_notice(email):
    send_email(
        to=email,
        subject="Реєстрація в NosiFit",
        text=(
            "Хтось (імовірно ви) намагався зареєструвати новий акаунт NosiFit "
            "з цією адресою. Акаунт із нею вже існує, тому код не надсилається.\n\n"
            "Увійдіть у свій акаунт або скористайтеся «Забули пароль?» на "
            "сторінці входу.\n\n"
            "Якщо це були не ви — просто проігноруйте цей лист."
        ),
    )


def _send_code_or_notice(email) -> None:
    """A code for a free address; for a registered one a notice instead.

    The page that follows is the same either way, so the registration form
    does not tell anyone which addresses have accounts. Raises EmailSendError.
    """
    if User.query.filter(db.func.lower(User.email) == email).first():
        VerificationCode.query.filter_by(email=email).delete()
        db.session.commit()
        send_existing_account_notice(email)
        return
    send_verification_email(email, _issue_code(email))


def _send_limited(email) -> bool:
    return hit_limit("verify-send-ip", client_ip(), *SEND_LIMIT_PER_IP) or hit_limit(
        "verify-send-email", email, *SEND_LIMIT_PER_EMAIL
    )


_issue_code = issue_code


@email_verification_bp.route("/send_code", methods=["POST"])
def send_code():
    email = normalize_email(request.form.get("email"))

    if not email:
        flash("Перевірте email: схоже, в адресі помилка", "error")
        return redirect(url_for("auth.register"))

    username = clean_username(request.form.get("username"))
    if not username:
        flash("Вкажіть ім'я користувача (до 50 символів).", "error")
        return redirect(url_for("auth.register"))

    password = request.form.get("password", "")
    problem = password_problem(password)
    if problem:
        flash(problem, "error")
        return redirect(url_for("auth.register"))

    confirm = request.form.get("confirm_password")
    if confirm is not None and confirm != password:
        flash("Паролі не збігаються.", "error")
        return redirect(url_for("auth.register"))

    # Limited before anything depends on whether the address is registered.
    if _send_limited(email):
        return too_many_requests("Забагато запитів коду. Спробуйте пізніше.")

    reg_data = {
        key: str(request.form.get(key))[:32]
        for key in REG_PROFILE_FIELDS
        if request.form.get(key)
    }
    reg_data.update(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
    )
    session["reg_data"] = reg_data
    session.pop("verified_email", None)

    try:
        _send_code_or_notice(email)
    except EmailSendError:
        flash("Не вдалося надіслати лист із кодом. Спробуйте трохи пізніше.", "error")
        return redirect(url_for("auth.register"))

    session["pending_email"] = email

    return redirect(url_for("email_verification.verify_email"))


@email_verification_bp.route("/verify_email", methods=["GET", "POST"])
def verify_email():
    if request.method == "GET":
        return render_template("auth/verify_email.html")

    code_input = request.form.get("code")
    email = session.get("pending_email")

    if not email:
        flash("Щось пішло не так. Почніть реєстрацію ще раз.", "error")
        return redirect(url_for("auth.register"))

    # Every attempt counts, whether or not a code exists for the address.
    if hit_limit("verify-attempts", email, MAX_CODE_ATTEMPTS, VERIFY_ATTEMPT_WINDOW):
        VerificationCode.query.filter_by(email=email).delete()
        db.session.commit()
        flash("Забагато спроб. Надішліть новий код.", "error")
        return redirect(url_for("email_verification.verify_email"))

    record = VerificationCode.query.filter_by(email=email).first()
    if record is not None and _is_expired(record):
        db.session.delete(record)
        db.session.commit()
        record = None

    # Missing (registered address), expired and wrong codes look the same.
    if record is None or not secrets.compare_digest(
        str(record.code), (code_input or "").strip()
    ):
        flash("Код невірний або застарів. Спробуйте ще раз або надішліть новий.", "error")
        return redirect(url_for("email_verification.verify_email"))

    session["verified_email"] = email
    session.pop("pending_email", None)

    db.session.delete(record)
    db.session.commit()
    reset_limit("verify-attempts", email)

    return redirect(url_for("auth.register_complete"))


@email_verification_bp.route("/resend", methods=["GET"], endpoint="resend")
def resend_code():
    email = session.get("pending_email")

    if not email:
        flash("Щось пішло не так. Почніть реєстрацію ще раз.", "error")
        return redirect(url_for("auth.register"))

    if _send_limited(email):
        flash("Забагато запитів коду. Спробуйте пізніше.", "error")
        return redirect(url_for("email_verification.verify_email"))

    try:
        _send_code_or_notice(email)
    except EmailSendError:
        flash("Не вдалося надіслати лист із кодом. Спробуйте трохи пізніше.", "error")
        return redirect(url_for("email_verification.verify_email"))

    flash("Новий код надіслано.", "info")
    return redirect(url_for("email_verification.verify_email"))


