"""Who may open the admin analytics.

Administrators are the accounts whose email is listed in the ADMIN_EMAILS
environment variable. There is no other way in: no role column, no default
account, no request parameter. Unset or empty means nobody.
"""

import re

_SEPARATORS = re.compile(r"[,;\s]+")


def parse_admin_emails(raw) -> frozenset:
    """"A@x.com, b@y.com;c@z.com" -> {"a@x.com", "b@y.com", "c@z.com"}."""
    if not isinstance(raw, str):
        return frozenset()
    return frozenset(
        part.strip().lower() for part in _SEPARATORS.split(raw) if "@" in part
    )


def is_admin(user, raw_admin_emails) -> bool:
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    email = (getattr(user, "email", "") or "").strip().lower()
    return bool(email) and email in parse_admin_emails(raw_admin_emails)
