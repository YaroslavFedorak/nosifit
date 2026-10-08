"""One place that sends email.

Production (Railway blocks SMTP ports) sends over HTTPS:
- Brevo when `BREVO_API_KEY` is set (free forever, 300 emails/day, a verified
  Gmail address works as the sender, no own domain needed);
- SendGrid when `SENDGRID_API_KEY` is set.
Otherwise, Flask-Mail + SMTP is used (local development with Gmail).
"""

import logging
from email.utils import parseaddr

import requests
from flask import current_app
from flask_mail import Message

from backend.app.extensions import mail

logger = logging.getLogger(__name__)

BREVO_URL = "https://api.brevo.com/v3/smtp/email"
SENDGRID_URL = "https://api.sendgrid.com/v3/mail/send"


class EmailSendError(RuntimeError):
    pass


def _sender() -> dict:
    # APIs want {"email", "name"}, not "Name <addr>".
    from_name, from_email = parseaddr(current_app.config.get("MAIL_FROM") or "")
    if not from_email:
        logger.error("MAIL_FROM is not set; the email API needs a verified sender")
        raise EmailSendError("Email sender is not configured")
    return {"email": from_email, "name": from_name or "NosiFit"}


def _post(service: str, url: str, payload: dict, headers: dict) -> None:
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
    except requests.RequestException as exc:
        logger.exception("%s request failed", service)
        raise EmailSendError("Email service is unavailable") from exc

    if response.status_code >= 400:
        logger.error("%s rejected email: %s %s", service, response.status_code, response.text[:500])
        raise EmailSendError("Email service rejected the message")


def _send_brevo(api_key: str, to: str, subject: str, text: str, html: str | None) -> None:
    payload = {
        "sender": _sender(),
        "to": [{"email": to}],
        "subject": subject,
        "textContent": text,
    }
    if html:
        payload["htmlContent"] = html

    _post(
        "Brevo",
        BREVO_URL,
        payload,
        {"api-key": api_key, "Content-Type": "application/json", "Accept": "application/json"},
    )


def _send_sendgrid(api_key: str, to: str, subject: str, text: str, html: str | None) -> None:
    payload = {
        "personalizations": [
            {
                "to": [{"email": to}],
            }
        ],
        "from": _sender(),
        "subject": subject,
        "content": [
            {"type": "text/plain", "value": text}
        ],
    }
    if html:
        payload["content"].append({"type": "text/html", "value": html})

    _post(
        "SendGrid",
        SENDGRID_URL,
        payload,
        {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )


def send_email(to: str, subject: str, text: str, html: str | None = None) -> None:
    """Send one email. Raises EmailSendError when it could not be sent."""
    brevo_key = current_app.config.get("BREVO_API_KEY")
    if brevo_key:
        _send_brevo(brevo_key, to, subject, text, html)
        return

    sendgrid_key = current_app.config.get("SENDGRID_API_KEY")
    if sendgrid_key:
        _send_sendgrid(sendgrid_key, to, subject, text, html)
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
        subject="Код підтвердження NosiFit",
        text=f"Ваш код підтвердження: {code}",
    )
