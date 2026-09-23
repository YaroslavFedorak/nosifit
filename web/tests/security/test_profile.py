from backend.app.extensions import db
from backend.app.models.user import User
from backend.app.models.oauth_account import OAuthAccount


def login(client):
    return client.post(
        "/auth/login",
        data={
            "email": "test@example.com",
            "password": "password123",
        },
    )


def test_profile_requires_login(client):
    response = client.get("/profile/")

    assert response.status_code == 302
    assert "/auth/login" in response.location


def test_profile_page(client, user):
    login(client)

    response = client.get("/profile/")

    assert response.status_code == 200


def test_profile_update_full(client, user):
    login(client)

    response = client.post(
        "/profile/update_full",
        data={
            "username": "updated",
            "email": "updated@example.com",
            "age": "25",
            "height": "180",
            "weight": "80",
            "gender": "male",
            "activity": "moderate",
            "goal": "maintenance",
            "experience": "beginner",
            "workouts_per_week": "3",
            "training_location": "gym",
            "wants_nutrition": "1",
            "wants_recovery": "1",
            "onboarding_completed": "1",
        },
    )

    assert response.status_code == 302

    db.session.refresh(user)

    assert user.username == "updated"
    assert user.email == "updated@example.com"
    assert user.profile.age == 25
    assert user.profile.height == 180
    assert user.profile.weight == 80
    assert user.profile.training_location == "gym"


def test_change_password_requires_login(client):
    response = client.post(
        "/profile/change_password",
        data={
            "current_password": "password123",
            "new_password": "new-password",
            "confirm_password": "new-password",
        },
    )

    assert response.status_code == 302
    assert "/auth/login" in response.location


def test_change_password_success(client, user):
    login(client)

    response = client.post(
        "/profile/change_password",
        data={
            "current_password": "password123",
            "new_password": "new-password",
            "confirm_password": "new-password",
        },
    )

    assert response.status_code == 200
    assert response.json["status"] == "success"


def test_change_password_wrong_old_password(client, user):
    login(client)

    response = client.post(
        "/profile/change_password",
        data={
            "current_password": "wrong-password",
            "new_password": "new-password",
            "confirm_password": "new-password",
        },
    )

    assert response.status_code == 400
    assert response.json["message"] == "wrong_old"


def test_change_email(client, user):
    login(client)

    response = client.post(
        "/profile/change_email",
        data={
            "new_email": "new@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 302
    assert response.location.endswith("/profile/")

    db.session.refresh(user)

    assert user.email == "new@example.com"


def test_change_email_requires_login(client):
    response = client.post(
        "/profile/change_email",
        data={
            "new_email": "new@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 302
    assert "/auth/login" in response.location


def test_oauth_disconnect(client, user):
    account = OAuthAccount(
        provider="github",
        provider_user_id="123",
        user_id=user.id,
    )

    db.session.add(account)
    db.session.commit()

    login(client)

    response = client.post(
        "/profile/oauth_disconnect",
        data={"provider": "github"},
    )

    assert response.status_code == 200
    assert response.json["message"] == "OAuth disconnected"
    assert OAuthAccount.query.count() == 0


def test_oauth_disconnect_missing_account(client, user):
    login(client)

    response = client.post(
        "/profile/oauth_disconnect",
        data={"provider": "github"},
    )

    assert response.status_code == 404


def test_delete_request(client, user, monkeypatch):
    login(client)

    monkeypatch.setattr(
        "web.app.routes.profile.delete_account_request.send_email_code",
        lambda email, code: None,
    )

    response = client.post("/profile/delete/request")

    assert response.status_code == 200
    assert response.json["status"] == "sent"

    with client.session_transaction() as session:
        assert "delete_code" in session
        assert session["delete_code_email"] == user.email


def test_delete_confirm(client, user, monkeypatch):
    login(client)

    monkeypatch.setattr(
        "web.app.routes.profile.delete_account_request.send_email_code",
        lambda email, code: None,
    )

    client.post("/profile/delete/request")

    with client.session_transaction() as session:
        code = session["delete_code"]

    response = client.post(
        "/profile/delete/confirm",
        json={"code": code},
    )

    assert response.status_code == 200
    assert response.json["status"] == "ok"


def test_delete_final(client, user, monkeypatch):
    login(client)

    monkeypatch.setattr(
        "web.app.routes.profile.delete_account_request.send_email_code",
        lambda email, code: None,
    )

    client.post("/profile/delete/request")

    with client.session_transaction() as session:
        code = session["delete_code"]

    client.post(
        "/profile/delete/confirm",
        json={"code": code},
    )

    response = client.post(
        "/profile/delete/final",
        json={
            "email": "test@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 200
    assert response.json["status"] == "deleted"

    assert User.query.filter_by(email="test@example.com").first() is None
