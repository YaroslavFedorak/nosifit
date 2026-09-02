from flask import url_for
from web.app.utils.token import generate_reset_token
from web.app import mail
from flask_mail import Message


def send_password_reset_email(user):
    token = generate_reset_token(user.email)
    reset_url = url_for("auth.reset_with_token", token=token, _external=True)

    msg = Message(
        subject="Відновлення паролю — NosiFit",
        recipients=[user.email],
        body=f"Щоб скинути пароль, перейдіть за посиланням:\n{reset_url}\n\nПосилання дійсне 1 годину.",
    )

    mail.send(msg)
