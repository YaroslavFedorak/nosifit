import pytest
from unittest.mock import patch


@patch("requests.post")
@patch("requests.get")
def test_github_no_email(mock_get, mock_post, client, app):
    app.config["GITHUB_CLIENT_ID"] = "TEST"
    app.config["GITHUB_CLIENT_SECRET"] = "SECRET"

    mock_post.return_value.json.return_value = {"access_token": "TOKEN"}

    mock_get.side_effect = [
        type("Resp", (), {"json": lambda: {"login": "noemailuser"}})(),
        type("Resp", (), {"json": lambda: []})(),
    ]

    response = client.get("/auth/github/callback?code=123")

    assert response.status_code == 302
    assert response.location.endswith("/auth/complete_profile")

    with client.session_transaction() as sess:
        assert sess["oauth_user"]["email"] is None


@patch("requests.post")
@patch("requests.get")
def test_github_secondary_email(mock_get, mock_post, client, app):
    app.config["GITHUB_CLIENT_ID"] = "TEST"
    app.config["GITHUB_CLIENT_SECRET"] = "SECRET"

    mock_post.return_value.json.return_value = {"access_token": "TOKEN"}

    mock_get.side_effect = [
        type("Resp", (), {"json": lambda: {"login": "secuser"}})(),
        type("Resp", (), {"json": lambda: [
            {"email": "secondary@example.com", "primary": False},
            {"email": "primary@example.com", "primary": True},
        ]})(),
    ]

    response = client.get("/auth/github/callback?code=123")

    assert response.status_code == 302
    assert response.location.endswith("/auth/complete_profile")

    with client.session_transaction() as sess:
        assert sess["oauth_user"]["email"] == "primary@example.com"


@patch("requests.post")
def test_github_token_error(mock_post, client, app):
    mock_post.return_value.json.return_value = {"error": "bad_verification_code"}

    response = client.get("/auth/github/callback?code=BAD")

    assert response.status_code == 400


@patch("requests.post")
@patch("requests.get")
def test_github_user_error(mock_get, mock_post, client, app):
    mock_post.return_value.json.return_value = {"access_token": "TOKEN"}

    mock_get.return_value.json.return_value = {"message": "Bad credentials"}

    response = client.get("/auth/github/callback?code=123")

    assert response.status_code == 400


@patch("requests.post")
@patch("requests.get")
def test_github_email_error(mock_get, mock_post, client, app):
    mock_post.return_value.json.return_value = {"access_token": "TOKEN"}

    mock_get.side_effect = [
        type("Resp", (), {"json": lambda: {"login": "user"}})(),
        type("Resp", (), {"json": lambda: {"message": "Bad credentials"}})(),
    ]

    response = client.get("/auth/github/callback?code=123")

    assert response.status_code == 400


@patch("requests.post")
@patch("requests.get")
def test_github_existing_email_login(mock_get, mock_post, client, app, user):
    mock_post.return_value.json.return_value = {"access_token": "TOKEN"}

    mock_get.side_effect = [
        type("Resp", (), {"json": lambda: {"login": "user"}})(),
        type("Resp", (), {"json": lambda: [
            {"email": "test@example.com", "primary": True}
        ]})(),
    ]

    response = client.get("/auth/github/callback?code=123")

    assert response.status_code == 302
    assert response.location.endswith("/profile")
