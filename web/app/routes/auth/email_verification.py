from flask import Blueprint, request, render_template, redirect, session, flash, url_for
from backend.app.models.verification_code import VerificationCode
from backend.app.models.user import User
from datetime import datetime, timedelta, timezone
import secrets

from backend.app.extensions import db
from backend.app.utils.mailer import EmailSendError, send_email

CODE_TTL = timedelta(minutes=10)
MAX_CODE_ATTEMPTS = 5

email_verification_bp = Blueprint("email_verification", __name__, url_prefix="/verify")


def _new_code() -> str:
    return f"{secrets.randbelow(900000) + 100000}"


def _is_expired(record) -> bool:
    created = record.created_at
    if created is None:
        return False
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - created > CODE_TTL


def send_verification_email(email, code):
    send_email(
        to=email,
        subject="Код підтвердження для NosiFit",
        text=(
            f"Привіт!\n\n"
            f"Ваш код підтвердження для створення акаунту в NosiFit:\n\n"
            f"👉 {code}\n\n"
            f"Код дійсний протягом 10 хвилин.\n"
            f"Якщо ви не надсилали запит — просто ігноруйте цей лист.\n\n"
            f"З повагою,\nКоманда NosiFit"
        ),
        html=f"""
    <h2>Ваш код підтвердження</h2>
    <p>Код для входу в <b>NosiFit</b>:</p>
    <h1 style="font-size: 32px; letter-spacing: 4px;">{code}</h1>
    <p>Дійсний 10 хвилин.</p>
    """,
    )


@email_verification_bp.route("/send_code", methods=["POST"])
def send_code():
    email = (request.form.get("email") or "").strip().lower()

    if not email:
        flash("Введіть коректний email", "error")
        return redirect(url_for("auth.register"))

    if User.query.filter_by(email=email).first():
        flash("Ця пошта вже зареєстрована. Увійдіть у свій акаунт.", "error")
        return redirect(url_for("auth.login"))

    session["reg_data"] = request.form.to_dict()

    code = _new_code()

    VerificationCode.query.filter_by(email=email).delete()

    db.session.add(VerificationCode(email=email, code=code))
    db.session.commit()

    try:
        send_verification_email(email, code)
    except EmailSendError:
        flash("Не вдалося надіслати лист із кодом. Спробуйте трохи пізніше.", "error")
        return redirect(url_for("auth.register"))

    session["pending_email"] = email
    session["code_attempts"] = 0

    return redirect(url_for("email_verification.verify_email"))


@email_verification_bp.route("/verify_email", methods=["GET", "POST"])
def verify_email():
    if request.method == "GET":
        return render_template("auth/verify_email.html")

    code_input = request.form.get("code")
    email = session.get("pending_email")

    if not email:
        flash("Сесія втрачена. Спробуйте ще раз.", "error")
        return redirect(url_for("auth.register"))

    record = VerificationCode.query.filter_by(email=email).first()

    if not record:
        flash("Код не знайдено. Спробуйте ще раз.", "error")
        return redirect(url_for("auth.register"))

    if _is_expired(record):
        db.session.delete(record)
        db.session.commit()
        flash("Код застарів. Надішліть новий.", "error")
        return redirect(url_for("email_verification.verify_email"))

    attempts = int(session.get("code_attempts", 0)) + 1
    session["code_attempts"] = attempts

    if attempts > MAX_CODE_ATTEMPTS:
        db.session.delete(record)
        db.session.commit()
        flash("Забагато спроб. Надішліть новий код.", "error")
        return redirect(url_for("email_verification.verify_email"))

    if not secrets.compare_digest(record.code, (code_input or "").strip()):
        flash("Невірний код.", "error")
        return redirect(url_for("email_verification.verify_email"))

    session["verified_email"] = email

    db.session.delete(record)
    db.session.commit()

    return redirect(url_for("auth.register_complete"))


@email_verification_bp.route("/resend", methods=["GET"], endpoint="resend")
def resend_code():
    email = session.get("pending_email")

    if not email:
        flash("Сесія втрачена. Спробуйте ще раз.", "error")
        return redirect(url_for("auth.register"))

    code = _new_code()

    VerificationCode.query.filter_by(email=email).delete()
    db.session.add(VerificationCode(email=email, code=code))
    db.session.commit()

    try:
        send_verification_email(email, code)
    except EmailSendError:
        flash("Не вдалося надіслати лист із кодом. Спробуйте трохи пізніше.", "error")
        return redirect(url_for("email_verification.verify_email"))

    session["code_attempts"] = 0
    flash("Код надіслано повторно!", "info")
    return redirect(url_for("email_verification.verify_email"))


