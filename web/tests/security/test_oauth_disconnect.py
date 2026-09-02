from web.app.models.oauth_account import OAuthAccount
from web.app import db


def test_disconnect_oauth(client, app, user):
    acc = OAuthAccount(provider="github", provider_user_id="123", user_id=user.id)
    db.session.add(acc)
    db.session.commit()

    client.post("/login", data={"email": "test@example.com", "password": "password123"})

    response = client.post("/profile/oauth_disconnect", data={"provider": "github"})

    assert response.status_code == 200
    assert OAuthAccount.query.count() == 0


def test_disconnect_nonexistent(client, user):
    client.post("/login", data={"email": "test@example.com", "password": "password123"})

    response = client.post("/profile/oauth_disconnect", data={"provider": "github"})

    assert response.status_code == 404


def test_cannot_disconnect_last_oauth(client, app, user):
    user.password = None
    db.session.add(user)
    db.session.add(
        OAuthAccount(provider="google", provider_user_id="123", user_id=user.id)
    )
    db.session.commit()

    client.post("/login", data={"email": "test@example.com", "password": "password123"})

    response = client.post("/profile/oauth_disconnect", data={"provider": "google"})

    assert response.status_code == 400
