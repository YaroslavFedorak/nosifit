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


def test_signed_in_user_opens_the_site_straight_into_the_dashboard(app, client, user):
    """After a redeploy and a browser restart: landing and the login page
    lead to the dashboard, no second sign-in."""
    log_in(client)
    cookies = cookies_after_login(client, "remember_token")

    browser = restarted_app(app.config["SECRET_KEY"]).test_client()
    browser.set_cookie("remember_token", cookies["remember_token"])

    for path in ("/", "/auth/login"):
        response = browser.get(path)
        assert response.status_code == 302 and response.location.endswith("/dashboard/")


def test_signed_out_visitor_sees_landing_and_login_form(app, client, user):
    assert client.get("/").status_code == 200
    assert client.get("/auth/login").status_code == 200

    log_in(client)
    client.get("/auth/logout")

    assert client.get("/").status_code == 200
    assert client.get("/auth/login").status_code == 200


def test_logo_takes_a_signed_in_user_to_the_landing(app, client, user):
    """Opening the site goes to the dashboard, but the logo in the app
    sidebar and the landing's own links show the landing, with a way back
    to the dashboard instead of the sign-in buttons."""
    log_in(client)

    dashboard = client.get("/dashboard/").get_data(as_text=True)
    assert 'href="/?home=1" class="cmp-sidebar-brand"' in dashboard

    response = client.get("/?home=1")
    assert response.status_code == 200
    landing = response.get_data(as_text=True)
    assert 'href="/dashboard/"' in landing
    assert 'href="/auth/login"' not in landing
    assert 'href="/auth/register"' not in landing
    # Its own logo and "Home" links keep the user on the landing.
    assert 'href="/"' not in landing

    assert client.get("/").location.endswith("/dashboard/")


def test_signed_out_visitor_sees_sign_in_buttons_on_the_landing(app, client, user):
    landing = client.get("/").get_data(as_text=True)
    assert 'href="/auth/login"' in landing
    assert 'href="/auth/register"' in landing
    assert 'href="/dashboard/"' not in landing
    assert 'href="/?home=1"' not in landing
    # The marker changes nothing for visitors.
    assert client.get("/?home=1").status_code == 200
