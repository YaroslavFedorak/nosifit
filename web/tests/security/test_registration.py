from unittest.mock import patch

from backend.app.extensions import db
from backend.app.models.user import User
from backend.app.models.verification_code import VerificationCode
from backend.app.models.oauth_account import OAuthAccount


def test_register_page(client):
    response = client.get("/auth/register")
    assert response.status_code == 200


@patch("web.app.routes.auth.email_verification.send_verification_email")
def test_registration_send_code(mock_send, client):
    response = client.post(
        "/verify/send_code",
        data={
            "username": "newuser",
            "email": "new@example.com",
            "password": "password123",
            "confirm": "password123",
        },
    )

    assert response.status_code == 302
    assert response.location.endswith("/verify/verify_email")

    record = VerificationCode.query.filter_by(
        email="new@example.com"
    ).first()

    assert record is not None
    assert len(record.code) == 6
    mock_send.assert_called_once()


@patch("web.app.routes.auth.email_verification.send_verification_email")
def test_registration_verify_code(mock_send, client):
    client.post(
        "/verify/send_code",
        data={
            "username": "newuser",
            "email": "new@example.com",
            "password": "password123",
            "confirm": "password123",
        },
    )

    record = VerificationCode.query.filter_by(
        email="new@example.com"
    ).first()

    response = client.post(
        "/verify/verify_email",
        data={"code": record.code},
    )

    assert response.status_code == 302
    assert response.location.endswith("/auth/register_complete")

    with client.session_transaction() as session:
        assert session["verified_email"] == "new@example.com"

    assert VerificationCode.query.filter_by(
        email="new@example.com"
    ).first() is None


@patch("web.app.routes.auth.email_verification.send_verification_email")
def test_registration_wrong_code(mock_send, client):
    client.post(
        "/verify/send_code",
        data={
            "username": "newuser",
            "email": "new@example.com",
            "password": "password123",
            "confirm": "password123",
        },
    )

    response = client.post(
        "/verify/verify_email",
        data={"code": "000000"},
    )

    assert response.status_code == 302
    assert response.location.endswith("/verify/verify_email")

    with client.session_transaction() as session:
        assert "verified_email" not in session


@patch("web.app.routes.auth.email_verification.send_verification_email")
def test_registration_complete_creates_user(mock_send, client):
    client.post(
        "/verify/send_code",
        data={
            "username": "newuser",
            "email": "new@example.com",
            "password": "password123",
            "confirm": "password123",
            "training_location": "home",
        },
    )

    record = VerificationCode.query.filter_by(
        email="new@example.com"
    ).first()

    client.post(
        "/verify/verify_email",
        data={"code": record.code},
    )

    response = client.post(
        "/auth/register_complete",
        data={
            "training_location": "home",
        },
    )

    assert response.status_code == 302
    assert response.location.endswith("/dashboard/")

    user = User.query.filter_by(email="new@example.com").first()

    assert user is not None
    assert user.username == "newuser"
    assert user.password != "password123"
    assert user.profile is not None


# --- Account enumeration through the registration form ----------------------------------


def _form(email):
    return {
        "username": "someone",
        "email": email,
        "password": "password123",
        "confirm_password": "password123",
    }


def _flashes(client):
    with client.session_transaction() as session:
        return [message for _, message in session.pop("_flashes", [])]


def test_registration_does_not_reveal_registered_emails(client, user, monkeypatch):
    codes, notices = [], []
    monkeypatch.setattr(
        "web.app.routes.auth.email_verification.send_verification_email",
        lambda email, code: codes.append(email),
    )
    monkeypatch.setattr(
        "web.app.routes.auth.email_verification.send_existing_account_notice",
        lambda email: notices.append(email),
    )

    new = client.post("/verify/send_code", data=_form("fresh@example.com"))
    existing = client.post("/verify/send_code", data=_form("test@example.com"))

    assert existing.status_code == new.status_code == 302
    assert existing.location == new.location
    assert codes == ["fresh@example.com"] and notices == ["test@example.com"]
    assert VerificationCode.query.filter_by(email="test@example.com").count() == 0

    client.post("/verify/verify_email", data={"code": "123456"})
    with client.session_transaction() as session:
        assert "verified_email" not in session


def test_missing_expired_and_wrong_codes_look_the_same(client, user, monkeypatch):
    from datetime import datetime, timedelta, timezone

    sent = {}
    monkeypatch.setattr(
        "web.app.routes.auth.email_verification.send_verification_email",
        lambda email, code: sent.update({email: code}),
    )
    monkeypatch.setattr(
        "web.app.routes.auth.email_verification.send_existing_account_notice",
        lambda email: None,
    )
    messages = []

    client.post("/verify/send_code", data=_form("test@example.com"))  # registered
    client.post("/verify/verify_email", data={"code": "123456"})
    messages.append(_flashes(client))

    client.post("/verify/send_code", data=_form("fresh@example.com"))
    wrong = "000000" if sent["fresh@example.com"] != "000000" else "111111"
    client.post("/verify/verify_email", data={"code": wrong})
    messages.append(_flashes(client))

    VerificationCode.query.update(
        {"created_at": datetime.now(timezone.utc) - timedelta(minutes=11)}
    )
    db.session.commit()
    client.post("/verify/verify_email", data={"code": sent["fresh@example.com"]})
    messages.append(_flashes(client))

    assert messages[0] == messages[1] == messages[2] and messages[0]
