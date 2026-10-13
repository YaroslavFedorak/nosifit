"""Emailed verification codes.

One code store, one expiry and one attempt counter per address, shared by
the website registration and the Telegram registration.
"""

import secrets
from datetime import datetime, timedelta, timezone

from backend.app.extensions import db
from backend.app.models.verification_code import VerificationCode
from backend.app.utils.rate_limit import reset_limit

CODE_TTL = timedelta(minutes=10)
MAX_CODE_ATTEMPTS = 5

# Each email costs quota and lands in someone's inbox: limit per address.
# Wrong codes are counted on the server, not in the (client-side,
# replayable) session cookie.
SEND_LIMIT_PER_EMAIL = (5, 60 * 60)
VERIFY_ATTEMPT_WINDOW = int(CODE_TTL.total_seconds())


def new_code() -> str:
    return f"{secrets.randbelow(900000) + 100000}"


def code_is_expired(record) -> bool:
    created = record.created_at
    if created is None:
        return False
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - created > CODE_TTL


def issue_code(email) -> str:
    code = new_code()
    VerificationCode.query.filter_by(email=email).delete()
    db.session.add(VerificationCode(email=email, code=code))
    db.session.commit()
    reset_limit("verify-attempts", email)
    return code
