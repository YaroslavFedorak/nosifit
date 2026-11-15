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
    assert client.get("/profile/account").status_code == 200


def test_profile_update_full(client, user):
    login(client)

    response = client.post(
        "/profile/update_full",
        data={
            "username": "updated",
            "email": "test@example.com",
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
    assert user.email == "test@example.com"
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


def test_profile_update_cannot_change_email(client, user):
    """Email changes need the emailed code; the profile form must not skip it."""
    login(client)

    response = client.post(
        "/profile/update_full",
        data={"username": "updated", "email": "attacker@example.com", "age": "25"},
    )

    assert response.status_code == 302
    db.session.refresh(user)
    assert user.email == "test@example.com"
    assert user.username == "testuser"


def test_change_email(client, user, monkeypatch):
    login(client)

    sent = {}
    monkeypatch.setattr(
        "web.app.routes.profile.email_change.send_email_code",
        lambda email, code: sent.update(email=email, code=code),
    )

    # The old-address notice is queued in the email outbox, not sent here.

    response = client.post(
        "/profile/change_email",
        json={"new_email": "new@example.com", "password": "password123"},
    )

    assert response.status_code == 200
    assert response.json["status"] == "sent"
    assert sent["email"] == "new@example.com"

    db.session.refresh(user)
    assert user.email == "test@example.com"

    response = client.post("/profile/confirm_email", json={"code": sent["code"]})

    assert response.status_code == 200
    assert response.json["status"] == "success"

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
        entry = session["delete_code"]
        assert entry["email"] == user.email
        assert entry["verified"] is False
        assert "code" not in entry


def test_delete_confirm(client, user, monkeypatch):
    login(client)

    sent = {}
    monkeypatch.setattr(
        "web.app.routes.profile.delete_account_request.send_email_code",
        lambda email, code: sent.update(code=code),
    )

    client.post("/profile/delete/request")

    # The session holds only a hash; the real code arrives by email.
    code = sent["code"]

    response = client.post(
        "/profile/delete/confirm",
        json={"code": code},
    )

    assert response.status_code == 200
    assert response.json["status"] == "ok"


def test_delete_final(client, user, monkeypatch):
    login(client)

    sent = {}
    monkeypatch.setattr(
        "web.app.routes.profile.delete_account_request.send_email_code",
        lambda email, code: sent.update(code=code),
    )

    client.post("/profile/delete/request")

    # The session holds only a hash; the real code arrives by email.
    code = sent["code"]

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


def test_profile_summary_requires_login(client):
    assert client.get("/profile/summary").status_code == 302


def test_profile_summary_describes_the_account(client, user):
    login(client)

    data = client.get("/profile/summary").get_json()

    assert data["user"]["email"] == "test@example.com"
    assert set(data["profile"]) >= {"age", "gender", "height", "weight", "activity", "goal", "training_location"}
    assert "fat_loss" in data["options"]["goals"]
    assert data["sign_in"]["has_password"] is True
    assert "password" not in str(data).lower().replace("has_password", "")


def test_profile_update_answers_json_when_asked(client, user):
    login(client)
    fields = {"username": "updated", "age": "30", "height": "175", "weight": "70", "gender": "female",
              "activity": "1.55", "goal": "fat_loss", "experience": "beginner", "workouts_per_week": "3",
              "training_location": "home"}

    response = client.post("/profile/update_full", data=fields, headers={"Accept": "application/json"})

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "ok"
    assert body["account"]["profile"]["age"] == 30
    assert body["account"]["user"]["name"] == "updated"

    bad = client.post("/profile/update_full", data={**fields, "age": "5"}, headers={"Accept": "application/json"})
    assert bad.status_code == 400
    assert bad.get_json() == {"status": "error", "message": "invalid_profile"}

