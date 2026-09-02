def test_register_success(client, app):
    response = client.post(
        "/register",
        data={
            "username": "newuser",
            "email": "new@example.com",
            "password": "password123",
            "confirm": "password123",
        },
    )

    assert response.status_code in (200, 302)

    from web.app.models.user import User

    user = User.query.filter_by(email="new@example.com").first()

    assert user is not None
    assert user.password != "password123"


def test_login_success(client, user):
    response = client.post(
        "/login", data={"email": "test@example.com", "password": "password123"}
    )

    assert response.status_code in (200, 302)


def test_logout(client, user):
    client.post("/login", data={"email": "test@example.com", "password": "password123"})

    response = client.get("/logout")

    assert response.status_code in (200, 302)


def test_delete_account(client, app, user):
    client.post("/login", data={"email": "test@example.com", "password": "password123"})

    response = client.post("/profile/delete")

    assert response.status_code in (200, 302)

    from web.app.models.user import User

    deleted = User.query.filter_by(email="test@example.com").first()

    assert deleted is None
