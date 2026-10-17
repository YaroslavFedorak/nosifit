"""Privacy policy page and the consent gate (auth/consent.py)."""

from datetime import datetime

import pytest
from flask import g
from werkzeug.security import generate_password_hash

from backend.app.extensions import db
from backend.app.models.oauth_account import OAuthAccount
from backend.app.models.telegram import TelegramIdentity
from backend.app.models.user import User
from backend.app.models.verification_code import VerificationCode
from backend.app.services.consent import CONSENT_VERSION, has_current_consent

PASSWORD = "password123"
BOTH = {"privacy_consent": "on", "health_consent": "on"}


@pytest.fixture
def plain_user(app, no_auto_consent):
    """A user as every existing account is right after the deploy: no consent."""
    u = User(
        username="plain",
        email="plain@example.com",
        password=generate_password_hash(PASSWORD),
        privacy_accepted_at=None,
    )
    db.session.add(u)
    db.session.commit()
    return u


def _login(client, email="plain@example.com"):
    response = client.post("/auth/login", data={"email": email, "password": PASSWORD})
    g.pop("_login_user", None)
    return response


def _get(client, path, **kwargs):
    g.pop("_login_user", None)
    return client.get(path, **kwargs)


def _post(client, path, **kwargs):
    g.pop("_login_user", None)
    return client.post(path, **kwargs)


# --- /privacy ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "locale, heading",
    [("uk", "Політика конфіденційності NosiFit"), ("en", "NosiFit Privacy Policy"), ("pl", "NosiFit Privacy Policy"), ("ru", "NosiFit Privacy Policy")],
)
def test_privacy_page_is_public_in_every_language(app, client, locale, heading):
    app.config.update(PRIVACY_CONTROLLER_NAME="Jane Owner", PRIVACY_CONTACT_EMAIL="privacy@example.com")
    client.set_cookie("nosifit_locale", locale)

    response = client.get("/privacy")
    text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert heading in text
    assert "Jane Owner" in text and "mailto:privacy@example.com" in text
    assert CONSENT_VERSION in text


def test_privacy_page_marks_missing_controller_details(app, client):
    app.config.update(PRIVACY_CONTROLLER_NAME="", PRIVACY_CONTACT_EMAIL="")
    client.set_cookie("nosifit_locale", "uk")

    text = client.get("/privacy").get_data(as_text=True)

    assert "володільця не вказано]" in text and "[email не вказано]" in text


def test_links_to_the_policy_resolve(client):
    register = client.get("/auth/register").get_data(as_text=True)
    assert 'href="/privacy"' in register
    assert 'name="privacy_consent"' in register and 'name="health_consent"' in register
    assert client.get("/privacy").status_code == 200


# --- The gate ---------------------------------------------------------------------


def test_pages_redirect_to_consent_and_back(client, plain_user):
    _login(client)

    response = _get(client, "/dashboard/")

    assert response.status_code == 302
    assert response.location.startswith("/consent?next=/dashboard/")


@pytest.mark.parametrize("path", ["/api/nutrition/day", "/api/v1/nutrition/day"])
def test_api_answers_consent_required(client, plain_user, path):
    _login(client)

    response = _get(client, path)

    assert response.status_code == 403
    assert response.get_json()["code"] == "consent_required"


def test_writes_are_refused_without_consent(client, plain_user):
    _login(client)

    water = _post(client, "/api/nutrition/water", json={"amount": 0.5})
    profile = _post(client, "/profile/update_full", json={"weight": 80})

    assert water.status_code == 403 and water.get_json()["code"] == "consent_required"
    assert profile.status_code == 403


def test_what_stays_open_without_consent(client, plain_user):
    _login(client)

    assert _get(client, "/privacy").status_code == 200
    assert _get(client, "/consent").status_code == 200
    assert _get(client, "/healthz").status_code == 200
    assert _get(client, "/").status_code in (200, 302)
    assert _get(client, "/consent").status_code == 200
    # Deleting the account is never blocked by the gate.
    delete = _post(client, "/profile/delete/request", json={})
    assert not (delete.status_code == 403 and (delete.get_json() or {}).get("code") == "consent_required")
    assert _get(client, "/auth/logout").status_code == 302


def test_anonymous_visitors_are_not_affected(client, no_auto_consent):
    assert client.get("/dashboard/").location.startswith("/auth/login")
    assert client.get("/api/nutrition/day").status_code == 401


# --- Giving consent -------------------------------------------------------------


@pytest.mark.parametrize("partial", [{}, {"privacy_consent": "on"}, {"health_consent": "on"}])
def test_both_consents_are_required(client, plain_user, partial):
    _login(client)

    _post(client, "/consent", data={**partial, "next": "/dashboard/"})

    db.session.refresh(plain_user)
    assert not has_current_consent(plain_user)
    assert plain_user.privacy_accepted_at is None and plain_user.health_data_consent_at is None


def test_consent_is_recorded_and_unlocks_the_app(client, plain_user):
    _login(client)

    response = _post(client, "/consent", data={**BOTH, "next": "/dashboard/"})

    assert response.status_code == 302 and response.location == "/dashboard/"
    db.session.refresh(plain_user)
    assert has_current_consent(plain_user)
    assert plain_user.consent_version == CONSENT_VERSION
    assert isinstance(plain_user.health_data_consent_at, datetime)
    assert _get(client, "/dashboard/").status_code == 200
    assert _get(client, "/api/nutrition/day").status_code == 200


@pytest.mark.parametrize("target", ["//evil.example/x", "https://evil.example/", "/\\evil.example"])
def test_consent_never_redirects_off_site(client, plain_user, target):
    _login(client)

    response = _post(client, "/consent", data={**BOTH, "next": target})

    assert response.location == "/dashboard/"


def test_a_new_policy_version_asks_again(client, plain_user):
    plain_user.privacy_accepted_at = plain_user.health_data_consent_at = datetime.utcnow()
    plain_user.consent_version = "2000-01-01"
    db.session.commit()
    _login(client)

    assert _get(client, "/api/nutrition/day").get_json()["code"] == "consent_required"


def test_consent_api(client, plain_user):
    assert client.post("/api/consent", json=BOTH).status_code == 401
    _login(client)

    missing = _post(client, "/api/consent", json={"privacy_consent": True})
    assert missing.status_code == 400 and missing.get_json()["code"] == "consent_missing"

    given = _post(client, "/api/v1/consent", json={"privacy_consent": True, "health_consent": True})
    assert given.status_code == 200 and given.get_json()["consent_version"] == CONSENT_VERSION
    db.session.refresh(plain_user)
    assert has_current_consent(plain_user)


def test_telegram_session_can_give_consent_and_is_otherwise_stopped(client, plain_user):
    identity = TelegramIdentity(user_id=plain_user.id, telegram_user_id=4242)
    db.session.add(identity)
    db.session.commit()
    with client.session_transaction() as session:
        session["_user_id"] = plain_user.get_id()
        session["_fresh"] = True
        session["tg_identity"] = identity.id

    blocked = _get(client, "/api/nutrition/day")
    assert blocked.status_code == 403 and blocked.get_json()["code"] == "consent_required"

    given = _post(client, "/api/consent", json={"privacy_consent": True, "health_consent": True})
    assert given.status_code == 200
    assert _get(client, "/api/nutrition/day").status_code == 200


# --- Registration -----------------------------------------------------------------


@pytest.fixture
def sent_codes(monkeypatch):
    sent = []
    monkeypatch.setattr(
        "web.app.routes.auth.email_verification.send_verification_email",
        lambda email, code: sent.append((email, code)),
    )
    return sent


FORM = {
    "username": "newbie",
    "email": "newbie@example.com",
    "password": "a-good-password",
    "confirm_password": "a-good-password",
    "weight": "80",
    "height": "180",
    "age": "30",
}


@pytest.mark.parametrize("partial", [{}, {"privacy_consent": "on"}, {"health_consent": "on"}])
def test_registration_without_both_consents_keeps_nothing(client, no_auto_consent, sent_codes, partial):
    response = client.post("/verify/send_code", data={**FORM, **partial})

    assert response.location.endswith("/auth/register")
    assert sent_codes == []
    assert VerificationCode.query.count() == 0
    with client.session_transaction() as session:
        assert "reg_data" not in session  # no weight/height/age kept


def test_registration_records_consent(client, no_auto_consent, sent_codes):
    client.post("/verify/send_code", data={**FORM, **BOTH})
    client.post("/verify/verify_email", data={"code": sent_codes[0][1]})
    response = client.post("/auth/register_complete", data={})

    assert response.location.endswith("/dashboard/")
    user = User.query.filter_by(email="newbie@example.com").one()
    assert has_current_consent(user)
    g.pop("_login_user", None)
    assert client.get("/dashboard/").status_code == 200  # no second consent screen


def test_registration_session_without_consent_cannot_complete(client, no_auto_consent):
    with client.session_transaction() as session:
        session["reg_data"] = {"username": "x", "email": "x@example.com", "password_hash": "h"}
        session["verified_email"] = "x@example.com"

    client.post("/auth/register_complete", data={})

    assert User.query.filter_by(email="x@example.com").first() is None


def _oauth_session(client, uid):
    with client.session_transaction() as session:
        session["oauth_user"] = {
            "provider": "github",
            "provider_user_id": uid,
            "username": "octo",
            "email": f"octo{uid}@example.com",
        }


PROFILE = {"age": "25", "height": "180", "weight": "75", "workouts": "3"}


def test_oauth_profile_without_consent_creates_nothing(client, no_auto_consent):
    _oauth_session(client, "901")

    response = client.post("/auth/complete_profile", data={**PROFILE, "privacy_consent": "on"})

    assert response.status_code == 200
    assert OAuthAccount.query.filter_by(provider_user_id="901").first() is None
    assert User.query.filter_by(email="octo901@example.com").first() is None


def test_oauth_profile_records_consent(client, no_auto_consent):
    _oauth_session(client, "902")

    response = client.post("/auth/complete_profile", data={**PROFILE, **BOTH})

    assert response.status_code == 302
    user = User.query.filter_by(email="octo902@example.com").one()
    assert has_current_consent(user)
