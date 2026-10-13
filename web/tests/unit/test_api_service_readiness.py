"""Could the API run as its own service? What the tests can show today.

``create_app(pages=False)`` builds the API without any page, sign-in form or
bot code. These tests run real requests against it, with a session cookie
issued by the full app (as a separate web service sharing SECRET_KEY would).
What they cannot show (cookie domain, CORS, deployment) is listed in
docs/api.md.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from backend.app.services import telegram_auth as tg
from backend.app.utils.bot_signature import sign_request
from web.app import create_app

ROOT = Path(__file__).resolve().parents[3]
BOT_SECRET = "readiness-bot-secret-" + "x" * 32


@pytest.fixture
def api_app(app):
    """The API alone, on the same database as the ``app`` fixture."""
    return create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": app.config["SQLALCHEMY_DATABASE_URI"],
            "TELEGRAM_BOT_API_SECRET": BOT_SECRET,
            "PUBLIC_BASE_URL": "https://nosifit.example",
        },
        pages=False,
    )


@pytest.fixture
def api_client(api_app):
    return api_app.test_client()


def signed_in_cookie(client, user):
    """Sign in on the full app (the web service) and return its cookie."""
    response = client.post("/auth/login", data={"email": user.email, "password": "password123"})
    assert response.status_code == 302
    cookie = client.get_cookie("session")
    assert cookie is not None
    return cookie.value


def test_the_api_app_serves_only_the_api(api_app):
    paths = {rule.rule for rule in api_app.url_map.iter_rules()}
    other = {p for p in paths if not p.startswith("/api/")}

    assert {p for p in other if not p.startswith("/static")} == {"/healthz"}
    assert len([p for p in paths if p.startswith("/api/v1/")]) > 50


def test_building_the_api_app_loads_no_page_or_bot_code():
    script = (
        "import sys\n"
        "from web.app import create_app\n"
        "create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'postgresql+psycopg://u@localhost/x_test'}, pages=False)\n"
        "loaded = sorted(n for n in sys.modules if n.startswith(('web.app.routes', 'telegram_bot')))\n"
        "print(loaded)\n"
    )
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    result = subprocess.run([sys.executable, "-c", script], cwd=ROOT, env=env, capture_output=True, text=True, check=True)

    assert result.stdout.strip() == "[]"


def test_health_check(api_client):
    response = api_client.get("/healthz")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_a_session_from_the_web_service_works_on_the_api(client, user, api_client):
    api_client.set_cookie("session", signed_in_cookie(client, user))

    for path in ("/api/nutrition/day", "/api/v1/nutrition/day", "/api/dashboard/today"):
        response = api_client.get(path)
        assert response.status_code == 200, path


def test_without_a_session_the_api_answers_401(api_client):
    response = api_client.get("/api/v1/nutrition/day")

    assert response.status_code == 401
    assert response.get_json()["code"] == "authentication_required"


def test_cross_site_writes_are_blocked(client, user, api_client):
    api_client.set_cookie("session", signed_in_cookie(client, user))

    response = api_client.post(
        "/api/v1/training/plans", json={"name": "x"}, headers={"Origin": "https://evil.example"}
    )

    assert response.status_code == 403


def test_errors_and_unknown_urls_are_json(api_client):
    response = api_client.get("/api/v1/no-such-thing")

    assert response.status_code == 404
    assert response.get_json()["code"] == "not_found"


def test_the_bot_link_token_needs_no_page_routes(api_client):
    """It used to build the link with url_for() on a web route: a 500 here."""
    body = json.dumps({"telegram_user_id": 444, "username": "bob_tg"}).encode()
    headers = sign_request(BOT_SECRET, "POST", "/api/telegram/link-token", body)

    response = api_client.post("/api/telegram/link-token", data=body, headers=headers, content_type="application/json")

    assert response.status_code == 200
    assert response.get_json()["url"].startswith("https://nosifit.example/auth/telegram/link/")


@pytest.mark.parametrize("via", [None, "google", "github", "password"])
def test_the_link_path_matches_the_web_route(app, via):
    token = "A" * 20 + "b-_" + "9" * 20
    with app.test_request_context():
        from flask import url_for

        expected = url_for("telegram_link.open_link", token=token, via=via)

    assert tg.link_page_path(token, via) == expected


def test_production_still_refuses_to_start_without_the_rate_limit_store(app):
    with pytest.raises(RuntimeError, match="RATELIMIT_REDIS_URL"):
        create_app(
            {
                "IS_PRODUCTION": True,
                "SECRET_KEY": "x" * 40,
                "SQLALCHEMY_DATABASE_URI": app.config["SQLALCHEMY_DATABASE_URI"],
                "RATELIMIT_REDIS_URL": None,
            },
            pages=False,
        )
