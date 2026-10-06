from flask import current_app, url_for

from backend.app.utils.mailer import EmailSendError, send_email
from backend.app.utils.token import generate_reset_token


def send_password_reset_email(user):
    token = generate_reset_token(user)
    base_url = (current_app.config.get("PUBLIC_BASE_URL") or "").rstrip("/")
    if base_url:
        reset_url = base_url + url_for("auth.reset_with_token", token=token)
    elif current_app.config.get("IS_PRODUCTION"):
        # Without a canonical URL the link would trust the request's Host.
        current_app.logger.error("PUBLIC_BASE_URL is not set; refusing to send a reset link")
        raise EmailSendError("PUBLIC_BASE_URL is not configured")
    else:
        reset_url = url_for("auth.reset_with_token", token=token, _external=True)

    send_email(
        to=user.email,
        subject="Відновлення паролю — NosiFit",
        text=(
            f"Щоб скинути пароль, перейдіть за посиланням:\n{reset_url}\n\n"
            "Посилання дійсне 1 годину."
        ),
    )
