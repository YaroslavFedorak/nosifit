"""Bearer tokens of the mobile apps as a way into the JSON API.

Flask-Login asks ``load_user_from_request`` only when the request has no
session user. A token is accepted on /api/ paths only: pages, sign-in forms
and account settings (email, password, deletion) stay with browser sessions.

Nothing is written to the session, so a token request never gets a session
or "remember me" cookie. Browsers never attach an Authorization header on
their own, so token requests need no CSRF check.
"""

from backend.app.services import mobile_auth
from shared.api_paths import API_PREFIX, unversioned

BEARER = "bearer"


def bearer_token(request) -> str | None:
    scheme, _, token = (request.headers.get("Authorization") or "").partition(" ")
    token = token.strip()
    if scheme.lower() != BEARER or not token:
        return None
    return token


def load_user_from_request(request):
    if not unversioned(request.path).startswith(API_PREFIX):
        return None
    token = bearer_token(request)
    if token is None:
        return None
    return mobile_auth.user_for_token(token)
