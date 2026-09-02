def test_login_wrong_password(client, user):
    response = client.post(
        "/login", data={"email": "test@example.com", "password": "wrongpass"}
    )
    assert response.status_code == 401


def test_login_wrong_email(client):
    response = client.post(
        "/login", data={"email": "unknown@example.com", "password": "password123"}
    )
    assert response.status_code == 404


def test_oauth_user_cannot_login_with_password(client, app):
    from web.app.models.user import User
    from web.app import db

    u = User(username="oauthuser", email="oauth@example.com", password="oauth")
    db.session.add(u)
    db.session.commit()

    response = client.post(
        "/login", data={"email": "oauth@example.com", "password": "anything"}
    )
    assert response.status_code == 403
