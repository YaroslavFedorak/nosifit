from unittest.mock import MagicMock, patch

from backend.app.extensions import db
from backend.app.models.oauth_account import OAuthAccount


def test_github_redirect(client, app):
    app.config["GITHUB_CLIENT_ID"] = "TEST_ID"

    response = client.get("/auth/github")

    assert response.status_code == 302
    assert "https://github.com/login/oauth/authorize" in response.location
    assert "client_id=TEST_ID" in response.location


@patch("web.app.routes.auth.oauth_github.requests.post")
@patch("web.app.routes.auth.oauth_github.requests.get")
def test_github_existing_user(mock_get, mock_post, client, user):
    mock_post.return_value.json.return_value = {
        "access_token": "TOKEN",
    }

    user_response = MagicMock()
    user_response.json.return_value = {
        "id": 123,
        "login": "testuser",
    }

    email_response = MagicMock()
    email_response.json.return_value = [
        {
            "email": "test@example.com",
            "primary": True,
            "verified": True,
        }
    ]

    mock_get.side_effect = [user_response, email_response]

    response = client.get("/auth/github/callback?code=123")

    assert response.status_code == 302
    assert response.location.endswith("/profile")


@patch("web.app.routes.auth.oauth_github.requests.post")
@patch("web.app.routes.auth.oauth_github.requests.get")
def test_github_new_user(mock_get, mock_post, client):
    mock_post.return_value.json.return_value = {
        "access_token": "TOKEN",
    }

    user_response = MagicMock()
    user_response.json.return_value = {
        "id": 456,
        "login": "newuser",
    }

    email_response = MagicMock()
    email_response.json.return_value = [
        {
            "email": "new@example.com",
            "primary": True,
            "verified": True,
        }
    ]

    mock_get.side_effect = [user_response, email_response]

    response = client.get("/auth/github/callback?code=123")

    assert response.status_code == 302
    assert response.location.endswith("/auth/complete_profile")

    with client.session_transaction() as session:
        assert session["oauth_user"]["email"] == "new@example.com"
        assert session["oauth_user"]["username"] == "newuser"
        assert session["oauth_user"]["provider"] == "github"


@patch("web.app.routes.auth.oauth_github.requests.post")
@patch("web.app.routes.auth.oauth_github.requests.get")
def test_github_private_email_uses_noreply(mock_get, mock_post, client, user):
    mock_post.return_value.json.return_value = {"access_token": "TOKEN"}

    user_response = MagicMock()
    user_response.json.return_value = {"id": 789, "login": "Hidden"}
    email_response = MagicMock()
    email_response.json.return_value = {"message": "Resource not accessible by integration"}
    mock_get.side_effect = [user_response, email_response]

    response = client.get("/auth/github/callback?code=123")

    assert response.location.endswith("/auth/complete_profile")
    with client.session_transaction() as session:
        assert session["oauth_user"]["email"] == "789+hidden@users.noreply.github.com"


@patch("web.app.routes.auth.oauth_github.requests.post")
@patch("web.app.routes.auth.oauth_github.requests.get")
def test_github_unverified_email_is_not_linked(mock_get, mock_post, client, user):
    mock_post.return_value.json.return_value = {"access_token": "TOKEN"}

    user_response = MagicMock()
    user_response.json.return_value = {"id": 321, "login": "attacker"}
    email_response = MagicMock()
    email_response.json.return_value = [
        {"email": "test@example.com", "primary": True, "verified": False}
    ]
    mock_get.side_effect = [user_response, email_response]

    response = client.get("/auth/github/callback?code=123")

    assert response.location.endswith("/auth/complete_profile")
    assert OAuthAccount.query.filter_by(provider_user_id="321").first() is None


def test_github_callback_without_code_redirects_to_login(client):
    response = client.get("/auth/github/callback")

    assert response.status_code == 302
    assert response.location.endswith("/auth/login")


def test_complete_profile_links_oauth_account(client):
    with client.session_transaction() as session:
        session["oauth_user"] = {
            "provider": "github",
            "provider_user_id": "555",
            "username": "octo",
            "email": "Octo@Example.com",
        }

    response = client.post(
        "/auth/complete_profile",
        data={"age": "25", "height": "180", "weight": "75", "workouts": "3"},
    )

    assert response.status_code == 302
    assert response.location.endswith("/profile")

    account = OAuthAccount.query.filter_by(provider="github", provider_user_id="555").first()
    assert account is not None
    assert account.user.email == "octo@example.com"


def test_complete_profile_rejects_empty_form(client):
    with client.session_transaction() as session:
        session["oauth_user"] = {
            "provider": "github",
            "provider_user_id": "556",
            "username": "octo2",
            "email": "octo2@example.com",
        }

    response = client.post("/auth/complete_profile", data={})

    assert response.status_code == 200
    assert OAuthAccount.query.filter_by(provider_user_id="556").first() is None


@patch("web.app.routes.auth.oauth_github.requests.post")
def test_github_token_error(mock_post, client):
    mock_post.return_value.json.return_value = {
        "error": "bad_verification_code",
    }

    response = client.get("/auth/github/callback?code=BAD")

    assert response.status_code == 400


def test_google_callback_existing_user(client, user):
    google = MagicMock()

    google.authorize_access_token.return_value = {
        "id_token": "TOKEN",
    }

    google.server_metadata = {
        "userinfo_endpoint": "https://example.com/userinfo",
    }

    google.get.return_value.json.return_value = {
        "sub": "GOOGLE123",
        "email": "test@example.com",
        "name": "Test User",
    }

    with patch(
        "web.app.routes.auth.oauth_google.oauth.create_client",
        return_value=google,
    ):
        response = client.get("/auth/google/callback")

    assert response.status_code == 302
    assert response.location.endswith("/profile")

    account = OAuthAccount.query.filter_by(
        provider="google",
        provider_user_id="GOOGLE123",
    ).first()

    assert account is not None
    assert account.user_id == user.id


def test_google_callback_new_user(client):
    google = MagicMock()

    google.authorize_access_token.return_value = {
        "id_token": "TOKEN",
    }

    google.server_metadata = {
        "userinfo_endpoint": "https://example.com/userinfo",
    }

    google.get.return_value.json.return_value = {
        "sub": "GOOGLE456",
        "email": "new@example.com",
        "name": "New User",
    }

    with patch(
        "web.app.routes.auth.oauth_google.oauth.create_client",
        return_value=google,
    ):
        response = client.get("/auth/google/callback")

    assert response.status_code == 302
    assert response.location.endswith("/auth/complete_profile")

    with client.session_transaction() as session:
        assert session["oauth_user"]["email"] == "new@example.com"
        assert session["oauth_user"]["provider"] == "google"


def test_google_invalid_token(client):
    google = MagicMock()
    google.authorize_access_token.side_effect = Exception("Invalid token")

    with patch(
        "web.app.routes.auth.oauth_google.oauth.create_client",
        return_value=google,
    ):
        response = client.get("/auth/google/callback")

    assert response.status_code == 400
