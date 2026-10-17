"""Consent to the privacy policy and to processing health data.

The service stores food, weight, sleep and training records, which are data
concerning health (GDPR art. 9): they are processed on explicit consent,
given separately from accepting the privacy policy. A user without both, for
the current policy version, is stopped by auth/consent.py until they give it.

Bump CONSENT_VERSION when the policy changes in a way users must agree to
again; the date of the policy text shown on /privacy is POLICY_DATE.
"""

from datetime import datetime

from backend.app.extensions import db

CONSENT_VERSION = "2026-10-18"
POLICY_DATE = "2026-10-18"


def has_current_consent(user) -> bool:
    return bool(
        user is not None
        and user.privacy_accepted_at is not None
        and user.health_data_consent_at is not None
        and user.consent_version == CONSENT_VERSION
    )


def apply_consent(user, now: datetime | None = None) -> None:
    """Mark both consents as given now (not committed)."""
    now = now or datetime.utcnow()
    user.privacy_accepted_at = now
    user.health_data_consent_at = now
    user.consent_version = CONSENT_VERSION


def record_consent(user) -> None:
    apply_consent(user)
    db.session.commit()


def consent_given(form_or_json) -> bool:
    """Both boxes ticked: the policy and, separately, health data."""
    def ticked(name):
        value = form_or_json.get(name)
        return value is True or (isinstance(value, str) and value.lower() in {"on", "true", "1", "yes"})

    return ticked("privacy_consent") and ticked("health_consent")
