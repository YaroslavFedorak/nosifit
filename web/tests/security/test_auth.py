from backend.app.models.user import User
from backend.app.extensions import db


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
