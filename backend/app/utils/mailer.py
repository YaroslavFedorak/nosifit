"""One place that sends email.

Production (Railway) blocks outgoing SMTP, so when ``RESEND_API_KEY`` is set
mail is sent through the Resend HTTP API. Without it, Flask-Mail + SMTP is
used (local development with Gmail).
"""

import logging

import requests
from flask import current_app
from flask_mail import Message

from backend.app.extensions import mail

logger = logging.getLogger(__name__)

RESEND_URL = "https://api.resend.com/emails"


class EmailSendError(RuntimeError):
    pass


def send_email(to: str, subject: str, text: str, html: str | None = None) -> None:
    """Send one email. Raises EmailSendError when it could not be sent."""
    api_key = current_app.config.get("RESEND_API_KEY")

    if api_key:
        payload = {
            "from": current_app.config.get("MAIL_FROM"),
            "to": [to],
            "subject": subject,
            "text": text,
        }
        if html:
            payload["html"] = html

        try:
            response = requests.post(
                RESEND_URL,
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10,
            )
        except requests.RequestException as exc:
            logger.exception("Resend request failed")
            raise EmailSendError("Email service is unavailable") from exc

        if response.status_code >= 400:
            logger.error("Resend rejected email: %s %s", response.status_code, response.text[:500])
            raise EmailSendError("Email service rejected the message")
        return

    message = Message(subject=subject, recipients=[to], body=text)
    if html:
        message.html = html

    try:
        mail.send(message)
    except Exception as exc:  # smtplib raises many different errors
        logger.exception("SMTP send failed")
        raise EmailSendError("Email could not be sent") from exc


def send_email_code(email, code):
    send_email(
        to=email,
        subject="Код підтвердження NOSIFIT",
        text=f"Ваш код підтвердження: {code}",
    )
