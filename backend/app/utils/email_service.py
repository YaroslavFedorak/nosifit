from flask import url_for

from backend.app.utils.mailer import send_email
from backend.app.utils.token import generate_reset_token


def send_password_reset_email(user):
    token = generate_reset_token(user.email)
    reset_url = url_for("auth.reset_with_token", token=token, _external=True)

    send_email(
        to=user.email,
        subject="Відновлення паролю — NosiFit",
        text=(
            f"Щоб скинути пароль, перейдіть за посиланням:\n{reset_url}\n\n"
            "Посилання дійсне 1 годину."
        ),
    )
