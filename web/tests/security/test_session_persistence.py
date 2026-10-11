"""Web sign-in survives a restart or redeploy.

Sessions and "remember me" cookies are signed with SECRET_KEY and resolved
against PostgreSQL (users table, see backend.app.utils.session_auth); the
server keeps nothing in memory or on disk. A new app instance with the same
SECRET_KEY and database is what a restart, redeploy or another gunicorn
worker looks like.
"""

import pytest
from flask import g

from backend.app.extensions import db
from web.app import create_app
from web.tests.conftest import TEST_DATABASE_URI

PROTECTED = "/api/nutrition/water"


def restarted_app(secret_key):
    return create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": TEST_DATABASE_URI,
            "SECRET_KEY": secret_key,
        }
    )


@pytest.fixture(autouse=True)
def per_request_user(app):
    """conftest keeps one app context (one ``g``) per test; load the user
    from each request's own cookies, as production does."""

    def forget_cached_user():
        g.pop("_login_user", None)

    app.before_request_funcs.setdefault(None, []).insert(0, forget_cached_user)


def log_in(client):
    response = client.post(
        "/auth/login", data={"email": "test@example.com", "password": "password123"}
    )
    assert response.status_code == 302 and response.location.endswith("/dashboard/")


def cookies_after_login(client, *names):
    return {name: client.get_cookie(name).value for name in names}


def test_session_cookie_survives_a_redeploy(app, client, user):
    log_in(client)
    cookies = cookies_after_login(client, "session")

    browser = restarted_app(app.config["SECRET_KEY"]).test_client()
    browser.set_cookie("session", cookies["session"])

    assert browser.get(PROTECTED).status_code == 200


def test_remember_cookie_survives_a_redeploy_and_a_browser_restart(app, client, user):
    """Browser closed (session cookie gone) and server redeployed."""
    log_in(client)
    cookies = cookies_after_login(client, "remember_token")

    browser = restarted_app(app.config["SECRET_KEY"]).test_client()
    browser.set_cookie("remember_token", cookies["remember_token"])

    assert browser.get(PROTECTED).status_code == 200
    # Flask-Login rebuilt the session from the remember cookie.
    assert browser.get_cookie("session") is not None


def test_logout_still_signs_out_after_a_redeploy(app, client, user):
    log_in(client)
    cookies = cookies_after_login(client, "session", "remember_token")

    browser = restarted_app(app.config["SECRET_KEY"]).test_client()
    for name, value in cookies.items():
        browser.set_cookie(name, value)
    assert browser.get(PROTECTED).status_code == 200

    browser.get("/auth/logout")

    assert browser.get_cookie("remember_token") is None
    assert browser.get(PROTECTED).status_code in (302, 401)


def test_password_change_revokes_cookies_across_redeploys(app, client, user):
    log_in(client)
    cookies = cookies_after_login(client, "session", "remember_token")

    user.set_password("a-new-password-1")
    db.session.commit()

    for name, value in cookies.items():
        browser = restarted_app(app.config["SECRET_KEY"]).test_client()
        browser.set_cookie(name, value)
        assert browser.get(PROTECTED).status_code in (302, 401)


def test_cookies_depend_on_a_stable_secret_key(app, client, user):
    """Why SECRET_KEY must be a fixed Railway variable, never generated at boot."""
    log_in(client)
    cookies = cookies_after_login(client, "session", "remember_token")

    browser = restarted_app("another-secret-key-" + "k" * 40).test_client()
    for name, value in cookies.items():
        browser.set_cookie(name, value)

    assert browser.get(PROTECTED).status_code in (302, 401)
