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


def _ticked(data, name) -> bool:
    value = data.get(name)
    return value is True or (isinstance(value, str) and value.lower() in {"on", "true", "1", "yes"})


def consent_given(form_or_json) -> bool:
    """Both boxes ticked: the policy and, separately, health data."""
    return _ticked(form_or_json, "privacy_consent") and _ticked(form_or_json, "health_consent")


def age_confirmed(form_or_json) -> bool:
    """"I am 16 or older": asked where no age is entered (/consent, the bot)."""
    return _ticked(form_or_json, "age_confirmed")


def too_young(user) -> bool:
    """The profile says the user is under the minimum age: no consent then."""
    from backend.app.utils.validation import MIN_ACCOUNT_AGE

    # The profile holds the age users enter; users.age is an older column.
    profile = getattr(user, "profile", None)
    ages = (getattr(profile, "age", None), getattr(user, "age", None))
    return any(isinstance(age, int) and age < MIN_ACCOUNT_AGE for age in ages)
