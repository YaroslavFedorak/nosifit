import pytest
from unittest.mock import patch
from web.app.models.oauth_account import OAuthAccount
from web.app import db


@patch("requests.post")
@patch("requests.get")
def test_github_connect_existing_user(mock_get, mock_post, client, app, user):
    app.config["GITHUB_CLIENT_ID"] = "TEST"
    app.config["GITHUB_CLIENT_SECRET"] = "SECRET"

    mock_post.return_value.json.return_value = {"access_token": "TOKEN"}

    mock_get.side_effect = [
        type("Resp", (), {"json": lambda: {"id": 999, "login": "yarik"}})(),
        type(
            "Resp",
            (),
            {"json": lambda: [{"email": "test@example.com", "primary": True}]},
        )(),
    ]

    response = client.get("/auth/github/callback?code=123")

    assert response.status_code == 302
    assert response.location.endswith("/profile")

    acc = OAuthAccount.query.filter_by(
        provider="github", provider_user_id="999"
    ).first()
    assert acc is not None
    assert acc.user_id == user.id


@patch("requests.post")
@patch("requests.get")
def test_github_connect_no_duplicate(mock_get, mock_post, client, app, user):
    db.session.add(
        OAuthAccount(provider="github", provider_user_id="999", user_id=user.id)
    )
    db.session.commit()

    mock_post.return_value.json.return_value = {"access_token": "TOKEN"}

    mock_get.side_effect = [
        type("Resp", (), {"json": lambda: {"id": 999, "login": "yarik"}})(),
        type(
            "Resp",
            (),
            {"json": lambda: [{"email": "test@example.com", "primary": True}]},
        )(),
    ]

    response = client.get("/auth/github/callback?code=123")

    assert response.status_code == 302
    assert OAuthAccount.query.count() == 1


@patch("authlib.integrations.flask_client.OAuth.authorize_access_token")
@patch("authlib.integrations.flask_client.OAuth.get")
def test_google_connect_existing_user(mock_get, mock_token, client, app, user):
    mock_token.return_value = {"id_token": "FAKE"}

    mock_get.return_value.json.return_value = {
        "sub": "GOOG123",
        "email": "test@example.com",
        "name": "Yarik",
    }

    response = client.get("/auth/google/callback")

    assert response.status_code == 302
    assert response.location.endswith("/profile")

    acc = OAuthAccount.query.filter_by(
        provider="google", provider_user_id="GOOG123"
    ).first()
    assert acc is not None
    assert acc.user_id == user.id
