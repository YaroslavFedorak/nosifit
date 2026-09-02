from flask import current_app
from flask_mail import Message
from web.app import mail


def send_email_code(email, code):
    msg = Message(
        subject="Код підтвердження NOSIFIT",
        recipients=[email],
        body=f"Ваш код підтвердження: {code}",
    )
    mail.send(msg)
