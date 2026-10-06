"""One place that sends email.

Production (Railway) uses SendGrid API when `SENDGRID_API_KEY` is set.
Otherwise, Flask-Mail + SMTP is used (local development with Gmail).
"""

import logging
from email.utils import parseaddr

import requests
from flask import current_app
from flask_mail import Message

from backend.app.extensions import mail

logger = logging.getLogger(__name__)

SENDGRID_URL = "https://api.sendgrid.com/v3/mail/send"


class EmailSendError(RuntimeError):
    pass


def send_email(to: str, subject: str, text: str, html: str | None = None) -> None:
    """Send one email. Raises EmailSendError when it could not be sent."""
    api_key = current_app.config.get("SENDGRID_API_KEY")

    if api_key:
        # SendGrid wants {"email", "name"}, not "Name <addr>".
        from_name, from_email = parseaddr(current_app.config.get("MAIL_FROM") or "")
        if not from_email:
            logger.error("MAIL_FROM is not set; SendGrid needs a verified sender")
            raise EmailSendError("Email sender is not configured")

        sender = {"email": from_email, "name": from_name or "NosiFit"}

        payload = {
            "personalizations": [
                {
                    "to": [{"email": to}],
                }
            ],
            "from": sender,
            "subject": subject,
            "content": [
                {"type": "text/plain", "value": text}
            ],
        }
        if html:
            payload["content"].append({"type": "text/html", "value": html})

        try:
            response = requests.post(
                SENDGRID_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                timeout=10,
            )
        except requests.RequestException as exc:
            logger.exception("SendGrid request failed")
            raise EmailSendError("Email service is unavailable") from exc

        if response.status_code >= 400:
            logger.error("SendGrid rejected email: %s %s", response.status_code, response.text[:500])
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
