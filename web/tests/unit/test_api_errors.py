"""Every error under /api/ has one JSON shape: code, message and error.

``code`` is stable and machine-readable, ``message`` human-readable and free
of internals, ``error`` keeps the value older clients read. Pages keep their
HTML errors and the sign-in redirect.
"""

import json
import re
import sys

import pytest

from backend.app.extensions import db
from backend.app.models.recovery.habit import RecoveryHabit
from backend.app.models.telegram import TelegramIdentity
from backend.app.utils.bot_signature import sign_request
from shared.api_paths import unversioned

BOT_SECRET = "error-shape-bot-secret-" + "x" * 32

CODE_RE = re.compile(r"^[a-z][a-z0-9_]*$")


@pytest.fixture
def signed_in(client, user):
    client.post("/auth/login", data={"email": user.email, "password": "password123"})
    return client


def assert_api_error(response, status, code=None):
    assert response.status_code == status
    assert response.mimetype == "application/json"
    body = response.get_json()
    assert CODE_RE.match(body["code"]), body
    assert isinstance(body["message"], str) and body["message"], body
    assert "error" in body
    if code is not None:
        assert body["code"] == code, body
    return body


def api_rules(app):
    for rule in app.url_map.iter_rules():
        if rule.rule.startswith("/api/"):
            for method in sorted(rule.methods - {"HEAD", "OPTIONS"}):
                yield rule.rule, method


def concrete(path):
    values = {"date": "2026-01-01", "date_string": "2026-01-01", "date_iso": "2026-01-01",
              "code": "4006381333931", "locale": "uk", "namespace": "common"}
    return re.sub(r"<(?:\w+:)?(\w+)>", lambda m: values.get(m.group(1), "1"), path)


# --- 401 instead of the sign-in page -----------------------------------------------


# Open without a session: the bot-signed Telegram API, translations and the
# injury catalog.
PUBLIC = {("/api/injuries/", "GET")}


def needs_session(rule, method):
    rule = unversioned(rule)
    return not rule.startswith(("/api/telegram/", "/api/i18n/")) and (rule, method) not in PUBLIC


def test_every_signed_in_api_answers_401_json_without_a_session(app, client):
    checked = 0
    for rule, method in api_rules(app):
        if not needs_session(rule, method):
            continue
        response = getattr(client, method.lower())(concrete(rule), json={})
        body = assert_api_error(response, 401, "authentication_required")
        assert body["message"] == "Authentication required"
        assert "Location" not in response.headers
        checked += 1
    assert checked >= 160  # both /api and /api/v1


def test_pages_still_redirect_to_the_sign_in_form(client):
    for path in ("/dashboard/", "/nutrition/", "/training/"):
        response = client.get(path, headers={"Accept": "application/json"})
        assert response.status_code == 302, path
        assert "/auth/login" in response.headers["Location"]


def test_a_fetch_from_the_website_gets_401_json(client):
    response = client.get(
        "/api/nutrition/day",
        headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"},
    )

    assert_api_error(response, 401, "authentication_required")


# --- Each status ---------------------------------------------------------------------


def test_400_validation_error_keeps_its_reason(signed_in):
    response = signed_in.post("/api/training/plans", json={"name": "   "})

    body = assert_api_error(response, 400, "invalid_input")
    assert body["message"] == "name must be text"
    assert body["error"] == "invalid_input"


def test_400_malformed_json(signed_in):
    response = signed_in.post("/api/nutrition/products", data="{not json", content_type="application/json")

    assert_api_error(response, 400, "bad_request")


def test_400_with_a_message_only_gets_a_code(signed_in):
    response = signed_in.get("/api/nutrition/day/not-a-date")

    body = assert_api_error(response, 400, "bad_request")
    assert body["error"] == body["message"] == "Invalid date"


def test_403_premium_only(signed_in):
    habit = RecoveryHabit(slug="sauna", name="Sauna", points=5, premium_only=True)
    db.session.add(habit)
    db.session.commit()

    response = signed_in.post(f"/api/recovery/habits/add/{habit.id}")

    body = assert_api_error(response, 403, "forbidden")
    assert body["error"] == body["message"] == "Premium required"


def test_403_cross_site_request(signed_in):
    response = signed_in.post("/api/training/plans", json={"name": "x"}, headers={"Origin": "https://evil.example"})

    body = assert_api_error(response, 403, "forbidden")
    assert body["message"] == "Cross-site request blocked"


def test_404_unknown_api_url(client):
    body = assert_api_error(client.get("/api/no-such-thing"), 404, "not_found")

    assert body["message"] == "Not found"


def test_404_page_stays_html(client):
    response = client.get("/no-such-page")

    assert response.status_code == 404
    assert response.mimetype == "text/html"


def test_404_specific_code(signed_in):
    response = signed_in.delete("/api/nutrition/meals/999")

    body = assert_api_error(response, 404, "meal_not_found")
    assert body["error"] == body["message"] == "Meal not found"


def test_405_lists_allowed_methods(signed_in):
    response = signed_in.delete("/api/nutrition/day")

    assert_api_error(response, 405, "method_not_allowed")
    assert "GET" in response.headers["Allow"]


def bot_post(client, path, payload):
    body = json.dumps(payload).encode()
    headers = sign_request(BOT_SECRET, "POST", path, body)
    return client.post(path, data=body, headers=headers, content_type="application/json")


@pytest.fixture
def bot_api(app):
    app.config["TELEGRAM_BOT_API_SECRET"] = BOT_SECRET


def test_409_from_the_bot_api(bot_api, client, user):
    db.session.add(TelegramIdentity(user_id=user.id, telegram_user_id=111))
    db.session.commit()

    response = bot_post(client, "/api/telegram/register/start", {"telegram_user_id": 111, "email": "a@b.co"})

    body = assert_api_error(response, 409, "already_linked")
    assert body["error"] == "already_linked"
    assert body["message"] == "Already linked"


def test_401_and_413_from_the_bot_api(bot_api, client):
    unsigned = client.post("/api/telegram/login", json={"telegram_user_id": 111})
    assert_api_error(unsigned, 401, "unauthorized")

    too_big = client.post("/api/telegram/login", data=b"x" * 5000, content_type="application/json")
    assert_api_error(too_big, 413, "payload_too_large")


def test_429_from_the_bot_api(bot_api, client, monkeypatch):
    from api.routes import telegram

    monkeypatch.setattr(telegram, "hit_limit", lambda *args: args[0] == "tg-login")

    body = assert_api_error(bot_post(client, "/api/telegram/login", {"telegram_user_id": 111}), 429, "rate_limited")
    assert body["error"] == "rate_limited"
    assert body["message"] == "Too many requests. Try again later."


def test_429_from_a_rate_limited_endpoint(app, signed_in, monkeypatch):
    module = sys.modules[app.view_functions["nutrition_api.api_barcode_lookup"].__module__]
    monkeypatch.setattr(module, "hit_limit", lambda *args: True)

    body = assert_api_error(signed_in.get("/api/nutrition/products/barcode/4006381333931"), 429, "rate_limited")
    assert body["message"] == "Too many requests. Try again later."


def test_500_hides_the_exception(app, signed_in, monkeypatch, caplog):
    from backend.app.services.dashboard.service import DashboardService

    def boom(*args):
        raise RuntimeError("password=hunter2 in /srv/secret.py")

    monkeypatch.setattr(DashboardService, "get_today", staticmethod(boom))
    app.config["PROPAGATE_EXCEPTIONS"] = False

    response = signed_in.get("/api/dashboard/today")

    body = assert_api_error(response, 500, "internal_server_error")
    assert body["message"] == "Internal server error"
    assert "hunter2" not in response.get_data(as_text=True)
    assert "Traceback" not in response.get_data(as_text=True)


def test_500_inside_an_endpoints_own_handler(app, signed_in, monkeypatch):
    from api.routes import training

    def boom(*args, **kwargs):
        raise RuntimeError("SELECT secret FROM users")

    monkeypatch.setattr(training.plan_service, "list_plans", boom)

    response = signed_in.get("/api/training/plans")

    assert_api_error(response, 500, "internal_server_error")
    assert "SELECT" not in response.get_data(as_text=True)


def test_503_when_the_rate_limiter_is_down(app, signed_in, monkeypatch):
    from backend.app.utils.rate_limit import RateLimitUnavailable

    module = sys.modules[app.view_functions["nutrition_api.api_barcode_lookup"].__module__]

    def down(*args):
        raise RateLimitUnavailable("redis down")

    monkeypatch.setattr(module, "hit_limit", down)

    response = signed_in.get("/api/nutrition/products/barcode/4006381333931")

    body = assert_api_error(response, 503, "rate_limit_unavailable")
    assert response.headers["Retry-After"] == "30"
    assert "redis" not in body["message"]


# --- Shape everywhere ------------------------------------------------------------------


def test_every_api_error_a_new_user_can_trigger_has_the_shape(app, signed_in):
    """Empty and malformed bodies against every signed-in endpoint."""
    for rule, method in api_rules(app):
        if not needs_session(rule, method) or method == "GET":
            continue
        for body in ({}, {"name": None, "date": "nope", "exercises": "x"}):
            response = getattr(signed_in, method.lower())(concrete(rule), json=body)
            if response.status_code >= 400:
                assert_api_error(response, response.status_code)


def test_web_json_errors_keep_their_format(signed_in):
    """JSON posts to pages (profile forms) are not part of the API."""
    response = signed_in.post("/profile/update_full", json={}, headers={"Origin": "https://evil.example"})

    assert response.status_code == 403
    assert set(response.get_json()) == {"error"}
