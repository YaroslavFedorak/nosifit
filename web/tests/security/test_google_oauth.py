import pytest
from unittest.mock import patch


def test_google_redirect(client, app):
    app.config["GOOGLE_CLIENT_ID"] = "GOOGLE_TEST"

    response = client.get("/auth/google")

    assert response.status_code == 302
    assert "accounts.google.com" in response.location
    assert "client_id=GOOGLE_TEST" in response.location


@patch("authlib.integrations.flask_client.OAuth.authorize_access_token")
@patch("authlib.integrations.flask_client.OAuth.parse_id_token")
def test_google_callback_existing_user(mock_parse, mock_token, client, app, user):
    mock_token.return_value = {"id_token": "FAKE"}
    mock_parse.return_value = {
        "email": "test@example.com",
        "name": "Test User",
        "sub": "12345"
    }

    response = client.get("/auth/google/callback")

    assert response.status_code == 302
    assert response.location.endswith("/profile")


@patch("authlib.integrations.flask_client.OAuth.authorize_access_token")
@patch("authlib.integrations.flask_client.OAuth.parse_id_token")
def test_google_callback_new_user(mock_parse, mock_token, client, app):
    mock_token.return_value = {"id_token": "FAKE"}
    mock_parse.return_value = {
        "email": "new@example.com",
        "name": "New User",
        "sub": "999"
    }

    response = client.get("/auth/google/callback")

    assert response.status_code == 302
    assert response.location.endswith("/auth/complete_profile")

    with client.session_transaction() as sess:
        assert sess["oauth_user"]["email"] == "new@example.com"


@patch("authlib.integrations.flask_client.OAuth.authorize_access_token")
def test_google_invalid_token(mock_token, client):
    mock_token.side_effect = Exception("Invalid token")

    response = client.get("/auth/google/callback")

    assert response.status_code == 400


@patch("authlib.integrations.flask_client.OAuth.authorize_access_token")
@patch("authlib.integrations.flask_client.OAuth.parse_id_token")
def test_google_no_email(mock_parse, mock_token, client):
    mock_token.return_value = {"id_token": "FAKE"}
    mock_parse.return_value = {"name": "User", "sub": "123"}

    response = client.get("/auth/google/callback")

    assert response.status_code == 400
