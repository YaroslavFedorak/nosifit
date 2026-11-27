"""Bearer-token sign-in of the Android and iOS apps (api/routes/mobile.py)."""

from datetime import datetime, timedelta, timezone

import pytest

from backend.app.extensions import db
from backend.app.models.mobile_token import MobileToken
from backend.app.services import mobile_auth
from backend.app.services.account_service import delete_user_account, withdraw_consent

LOGIN = "/api/v1/mobile/auth/login"


def sign_in(client, email="test@example.com", password="password123", **extra):
    body = {"email": email, "password": password, "platform": "android", **extra}
    return client.post(LOGIN, json=body)


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def fresh_user_per_request(app):
    """The test client keeps one app context, so Flask-Login's cached user
    would carry over between requests; a real server never does that."""
    from flask import g

    def forget():
        g.pop("_login_user", None)

    app.before_request_funcs.setdefault(None, []).insert(0, forget)


@pytest.fixture
def token(client, user):
    response = sign_in(client, device_name="Pixel 8")
    assert response.status_code == 200, response.get_json()
    return response.get_json()["token"]


def test_login_returns_a_token_and_the_account(client, user):
    response = sign_in(client, email="  TEST@example.com ", device_name="Pixel 8")
    assert response.status_code == 200
    data = response.get_json()
    assert data["token"].startswith(mobile_auth.TOKEN_PREFIX)
    assert data["token_type"] == "Bearer"
    assert data["user"] == {"id": user.id, "name": user.username, "email": user.email}
    assert data["consent_required"] is False
    # Only the hash is stored.
    row = MobileToken.query.one()
    assert row.token_hash == mobile_auth.hash_token(data["token"])
    assert data["token"] not in (row.token_hash, row.fingerprint)
    assert (row.platform, row.device_name) == ("android", "Pixel 8")


def test_login_sets_no_session_cookie(client, user):
    response = sign_in(client)
    assert response.status_code == 200
    assert not [c for c in response.headers.getlist("Set-Cookie") if c.startswith(("session=", "remember_token="))]


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"email": "test@example.com", "platform": "android"},
        {"email": 5, "password": "password123", "platform": "android"},
        {"email": "test@example.com", "password": "password123"},
        {"email": "test@example.com", "password": "password123", "platform": "windows"},
    ],
)
def test_login_rejects_incomplete_requests(client, user, body):
    response = client.post(LOGIN, json=body)
    assert response.status_code == 400
    assert response.get_json()["code"] == "invalid_input"


def test_wrong_password_and_unknown_email_get_the_same_answer(client, user):
    wrong = sign_in(client, password="nope-nope")
    unknown = sign_in(client, email="nobody@example.com")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.get_json() == unknown.get_json()
    assert wrong.get_json()["code"] == "invalid_credentials"
    assert MobileToken.query.count() == 0


def test_login_is_rate_limited_per_email(client, user):
    for _ in range(10):
        sign_in(client, password="wrong-password")
    response = sign_in(client)
    assert response.status_code == 429
    assert response.get_json()["code"] == "rate_limited"


def test_the_token_opens_the_api(client, token):
    assert client.get("/api/v1/dashboard/today").status_code == 401
    response = client.get("/api/v1/dashboard/today", headers=bearer(token))
    assert response.status_code == 200
    assert "daily_score" in response.get_json()
    # The unversioned alias accepts it as well.
    assert client.get("/api/dashboard/today", headers=bearer(token)).status_code == 200


def test_the_token_can_write(client, token):
    response = client.post("/api/v1/nutrition/water", json={"amount": 0.25}, headers=bearer(token))
    assert response.status_code == 200, response.get_json()


def test_the_token_does_not_open_pages(client, token):
    response = client.get("/profile/summary", headers=bearer(token))
    assert response.status_code in (302, 401)


def test_session_info(client, user, token):
    response = client.get("/api/v1/mobile/auth/session", headers=bearer(token))
    assert response.status_code == 200
    assert response.get_json()["user"]["id"] == user.id


@pytest.mark.parametrize("header", ["Bearer nfm_not-a-real-token", "Bearer ", "Basic abc", "nfm_x"])
def test_bad_tokens_are_refused(client, user, header):
    response = client.get("/api/v1/dashboard/today", headers={"Authorization": header})
    assert response.status_code == 401
    assert response.get_json()["code"] == "authentication_required"


def test_logout_revokes_the_token(client, token):
    assert client.post("/api/v1/mobile/auth/logout", headers=bearer(token)).status_code == 200
    assert MobileToken.query.count() == 0
    assert client.get("/api/v1/dashboard/today", headers=bearer(token)).status_code == 401


def test_a_password_change_revokes_the_token(client, user, token):
    user.set_password("a-brand-new-password")
    db.session.commit()
    assert client.get("/api/v1/dashboard/today", headers=bearer(token)).status_code == 401
    assert MobileToken.query.count() == 0


def test_an_expired_token_is_refused(client, token):
    row = MobileToken.query.one()
    row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.session.commit()
    assert client.get("/api/v1/dashboard/today", headers=bearer(token)).status_code == 401
    assert MobileToken.query.count() == 0


def test_old_sign_ins_are_dropped_beyond_the_limit(client, user):
    tokens = [sign_in(client).get_json()["token"] for _ in range(mobile_auth.MAX_TOKENS_PER_USER + 2)]
    assert MobileToken.query.count() == mobile_auth.MAX_TOKENS_PER_USER
    assert client.get("/api/v1/mobile/auth/session", headers=bearer(tokens[-1])).status_code == 200


def test_deleting_the_account_removes_its_tokens(client, user, token):
    delete_user_account(user)
    assert MobileToken.query.count() == 0
    assert client.get("/api/v1/dashboard/today", headers=bearer(token)).status_code == 401


def test_withdrawing_consent_keeps_the_app_signed_in(client, user, token):
    withdraw_consent(user)
    response = client.get("/api/v1/mobile/auth/session", headers=bearer(token))
    assert response.status_code == 200
    assert response.get_json()["consent_required"] is True


def test_without_consent_the_app_is_told_and_the_rest_is_closed(client, no_auto_consent, user):
    response = sign_in(client)
    assert response.status_code == 200
    data = response.get_json()
    assert data["consent_required"] is True
    headers = bearer(data["token"])
    assert client.get("/api/v1/mobile/auth/session", headers=headers).get_json()["consent_required"] is True
    closed = client.get("/api/v1/dashboard/today", headers=headers)
    assert closed.status_code == 403
    assert closed.get_json()["code"] == "consent_required"

    given = client.post(
        "/api/v1/consent",
        json={"privacy_consent": True, "health_consent": True, "age_confirmed": True},
        headers=headers,
    )
    assert given.status_code == 200, given.get_json()
    assert client.get("/api/v1/dashboard/today", headers=headers).status_code == 200
