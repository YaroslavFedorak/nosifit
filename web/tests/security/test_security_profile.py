def test_profile_requires_login(client):
    response = client.get("/profile")
    assert response.status_code == 302
    assert "/login" in response.location


def test_user_cannot_update_profile_without_login(client):
    response = client.post("/profile/update_name", json={"username": "new"})
    assert response.status_code == 401


def test_user_cannot_update_other_user_profile(client, app, user):
    client.post("/login", data={"email": "test@example.com", "password": "password123"})

    from web.app.models.user import User
    from web.app import db

    other = User(username="other", email="other@example.com", password="hashed")
    db.session.add(other)
    db.session.commit()

    response = client.post(
        "/profile/update_body",
        json={
            "age": 99,
            "height": 180,
            "weight": 80,
            "gender": "male",
            "user_id": other.id,
        },
    )

    assert response.status_code in (401, 403)


def test_change_password_requires_login(client):
    response = client.post(
        "/profile/change_password",
        json={"old_password": "123", "new_password": "456", "confirm_password": "456"},
    )
    assert response.status_code == 401


def test_oauth_user_cannot_change_password(client, app):
    from web.app.models.user import User
    from web.app import db

    u = User(username="oauth", email="oauth@example.com", password="oauth")
    db.session.add(u)
    db.session.commit()

    client.post("/login", data={"email": "oauth@example.com", "password": "anything"})

    response = client.post(
        "/profile/change_password",
        json={
            "old_password": "anything",
            "new_password": "newpass",
            "confirm_password": "newpass",
        },
    )

    assert response.status_code in (401, 403)


def test_change_email_requires_login(client):
    response = client.post(
        "/profile/change_email", json={"new_email": "new@example.com"}
    )
    assert response.status_code == 401


def test_change_password_requires_login(client):
    response = client.post(
        "/profile/change_password",
        json={"old_password": "123", "new_password": "456", "confirm_password": "456"},
    )
    assert response.status_code == 401


def test_change_password_wrong_old_password(client, app, user):
    client.post("/login", data={"email": "test@example.com", "password": "password123"})

    response = client.post(
        "/profile/change_password",
        json={
            "old_password": "wrong",
            "new_password": "newpass123",
            "confirm_password": "newpass123",
        },
    )

    assert response.status_code == 400


def test_change_password_mismatch(client, app, user):
    client.post("/login", data={"email": "test@example.com", "password": "password123"})

    response = client.post(
        "/profile/change_password",
        json={
            "old_password": "password123",
            "new_password": "newpass123",
            "confirm_password": "different",
        },
    )

    assert response.status_code == 400


def test_oauth_user_cannot_change_password(client, app):
    from web.app.models.user import User
    from web.app import db

    u = User(username="oauth", email="oauth@example.com", password="oauth")
    db.session.add(u)
    db.session.commit()

    client.post("/login", data={"email": "oauth@example.com", "password": "anything"})

    response = client.post(
        "/profile/change_password",
        json={
            "old_password": "anything",
            "new_password": "newpass",
            "confirm_password": "newpass",
        },
    )

    assert response.status_code in (401, 403)


def test_change_email_requires_login(client):
    response = client.post(
        "/profile/change_email", json={"new_email": "new@example.com"}
    )
    assert response.status_code == 401


def test_change_email_invalid_format(client, app, user):
    client.post("/login", data={"email": "test@example.com", "password": "password123"})

    response = client.post("/profile/change_email", json={"new_email": "not-an-email"})

    assert response.status_code == 400


def test_change_email_already_taken(client, app, user):
    from web.app.models.user import User
    from web.app import db

    other = User(username="other", email="other@example.com", password="123")
    db.session.add(other)
    db.session.commit()

    client.post("/login", data={"email": "test@example.com", "password": "password123"})

    response = client.post(
        "/profile/change_email", json={"new_email": "other@example.com"}
    )

    assert response.status_code == 400


def test_confirm_email_wrong_code(client, app, user):
    client.post("/login", data={"email": "test@example.com", "password": "password123"})

    with client.session_transaction() as sess:
        sess["email_change_code"] = "123456"
        sess["email_change_new"] = "new@example.com"

    response = client.post("/profile/confirm_email", json={"code": "000000"})

    assert response.status_code == 400


def test_confirm_email_success(client, app, user):
    client.post("/login", data={"email": "test@example.com", "password": "password123"})

    with client.session_transaction() as sess:
        sess["email_change_code"] = "123456"
        sess["email_change_new"] = "new@example.com"

    response = client.post("/profile/confirm_email", json={"code": "123456"})

    assert response.status_code == 200
