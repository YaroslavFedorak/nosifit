from backend.app.extensions import db
from backend.app.models.oauth_account import OAuthAccount
from backend.app.models.user import User


def test_login_page(client):
    response = client.get("/auth/login")
    assert response.status_code == 200


def test_login_success(client, user):
    response = client.post(
        "/auth/login",
        data={
            "email": "test@example.com",
            "password": "password123",
        },
    )
    assert response.status_code == 302
    assert response.location.endswith("/dashboard/")


def test_login_wrong_password(client, user):
    response = client.post(
        "/auth/login",
        data={
            "email": "test@example.com",
            "password": "wrong-password",
        },
    )
    assert response.status_code == 302
    assert response.location.endswith("/auth/login")


def test_login_unknown_user(client):
    response = client.post(
        "/auth/login",
        data={
            "email": "unknown@example.com",
            "password": "password123",
        },
    )
    assert response.status_code == 302
    assert response.location.endswith("/auth/login")


def test_logout(client, user):
    client.post(
        "/auth/login",
        data={
            "email": "test@example.com",
            "password": "password123",
        },
    )
    response = client.get("/auth/logout")
    assert response.status_code == 302
    assert response.location.endswith("/")


def test_oauth_user_cannot_login_with_password(client, app):
    user = User(
        username="oauthuser",
        email="oauth@example.com",
        password="not-used",
    )
    db.session.add(user)
    db.session.commit()

    account = OAuthAccount(
        provider="github",
        provider_user_id="oauth-123",
        user_id=user.id,
    )
    db.session.add(account)
    db.session.commit()

    response = client.post(
        "/auth/login",
        data={
            "email": "oauth@example.com",
            "password": "not-used",
        },
    )

    assert response.status_code == 302
    assert response.location.endswith("/auth/login")


def test_login_wrong_email(client):
    response = client.post(
        "/auth/login",
        data={
            "email": "missing@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 302
    assert response.location.endswith("/auth/login")
