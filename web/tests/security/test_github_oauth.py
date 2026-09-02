import pytest
from unittest.mock import patch


def test_github_redirect(client, app):
    app.config["GITHUB_CLIENT_ID"] = "TEST_ID"

    response = client.get("/auth/github")

    assert response.status_code == 302
    assert "https://github.com/login/oauth/authorize" in response.location
    assert "client_id=TEST_ID" in response.location


@patch("requests.post")
@patch("requests.get")
def test_github_callback_existing_user(mock_get, mock_post, client, app, user):
    app.config["GITHUB_CLIENT_ID"] = "TEST_ID"
    app.config["GITHUB_CLIENT_SECRET"] = "TEST_SECRET"

    mock_post.return_value.json.return_value = {
        "access_token": "FAKE_TOKEN"
    }

    mock_get.side_effect = [
        type("Resp", (), {"json": lambda: {"login": "testuser"}})(),
        type("Resp", (), {"json": lambda: [{"email": "test@example.com", "primary": True}]} )(),
    ]

    response = client.get("/auth/github/callback?code=123")

    assert response.status_code == 302
    assert response.location.endswith("/profile")


@patch("requests.post")
@patch("requests.get")
def test_github_callback_new_user(mock_get, mock_post, client, app):
    app.config["GITHUB_CLIENT_ID"] = "TEST_ID"
    app.config["GITHUB_CLIENT_SECRET"] = "TEST_SECRET"

    mock_post.return_value.json.return_value = {
        "access_token": "FAKE_TOKEN"
    }

    mock_get.side_effect = [
        type("Resp", (), {"json": lambda: {"login": "newuser"}})(),
        type("Resp", (), {"json": lambda: [{"email": "new@example.com", "primary": True}]} )(),
    ]

    response = client.get("/auth/github/callback?code=123")

    assert response.status_code == 302
    assert response.location.endswith("/auth/complete_profile")

    # Перевіряємо session
    with client.session_transaction() as sess:
        assert sess["oauth_user"]["email"] == "new@example.com"
        assert sess["oauth_user"]["username"] == "newuser"
        assert sess["oauth_user"]["provider"] == "github"
