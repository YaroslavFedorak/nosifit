"""/api/v1/... and the unversioned /api/... aliases behave the same.

Both are registrations of the same blueprints (api.register_api), so the
views, hooks and services are shared; these tests pin that down from the
outside: same rules, same answers, same security checks.
"""

import json
import re

import pytest

from backend.app.extensions import db
from backend.app.models.telegram import TelegramIdentity
from backend.app.utils.bot_signature import sign_request
from shared.api_paths import API_V1_PREFIX, unversioned

BOT_SECRET = "v1-contract-bot-secret-" + "x" * 32
VALUES = {"date": "2026-01-01", "date_string": "2026-01-01", "date_iso": "2026-01-01",
          "code": "4006381333931", "locale": "uk", "namespace": "common"}


def concrete(path):
    return re.sub(r"<(?:\w+:)?(\w+)>", lambda m: VALUES.get(m.group(1), "1"), path)


def v1(path):
    assert path.startswith("/api/") and not path.startswith(API_V1_PREFIX)
    return API_V1_PREFIX + path[len("/api/"):]


def legacy_rules(app):
    return [
        (rule.rule, sorted(rule.methods - {"HEAD", "OPTIONS"}), rule.endpoint)
        for rule in app.url_map.iter_rules()
        if rule.rule.startswith("/api/") and not rule.rule.startswith(API_V1_PREFIX)
    ]


@pytest.fixture
def signed_in(client, user):
    client.post("/auth/login", data={"email": user.email, "password": "password123"})
    return client


def same_answer(first, second):
    assert first.status_code == second.status_code
    assert first.mimetype == second.mimetype
    if first.is_json:
        assert first.get_json() == second.get_json()
    else:
        assert first.get_data() == second.get_data()


def test_every_api_rule_has_a_v1_twin_served_by_the_same_view(app):
    endpoints = {
        (rule.rule, method): rule.endpoint
        for rule in app.url_map.iter_rules()
        if rule.rule.startswith("/api/")
        for method in rule.methods - {"HEAD", "OPTIONS"}
    }
    legacy = {key: endpoint for key, endpoint in endpoints.items() if not key[0].startswith(API_V1_PREFIX)}
    versioned = {key: endpoint for key, endpoint in endpoints.items() if key[0].startswith(API_V1_PREFIX)}
    assert len(legacy) > 90

    for (path, method), endpoint in legacy.items():
        twin = versioned[(v1(path), method)]
        assert app.view_functions[twin] is app.view_functions[endpoint], (method, path)

    # Nothing exists only under v1.
    assert set(versioned) == {(v1(path), method) for path, method in legacy}


def test_guests_get_the_same_answers(app, client):
    for path, methods, _ in legacy_rules(app):
        if path.startswith("/api/telegram/"):
            continue  # bot-signed: covered below
        for method in methods:
            call = getattr(client, method.lower())
            same_answer(call(concrete(path), json={}), call(v1(concrete(path)), json={}))


def test_signed_in_reads_get_the_same_answers(app, signed_in):
    meal = signed_in.post("/api/nutrition/meals", json={"category": "lunch"}).get_json()
    signed_in.post("/api/nutrition/items", json={"meal_id": meal["id"], "name": "Rice", "calories": 130,
                                                "protein": 2.7, "fat": 0.3, "carbs": 28})
    signed_in.post("/api/nutrition/water", json={"amount": 0.5})
    signed_in.post("/api/training/plans", json={"name": "Push", "is_active": True})

    compared = 0
    for path, methods, _ in legacy_rules(app):
        if "GET" not in methods or path.startswith("/api/telegram/"):
            continue
        same_answer(signed_in.get(concrete(path)), signed_in.get(v1(concrete(path))))
        compared += 1
    assert compared > 40


def test_a_write_through_v1_is_read_through_the_alias(signed_in):
    meal = signed_in.post("/api/v1/nutrition/meals", json={"category": "dinner"})
    assert meal.status_code in (200, 201)

    day = signed_in.get("/api/nutrition/day").get_json()
    assert [m["id"] for m in day["meals"]] == [meal.get_json()["id"]]

    assert signed_in.delete(f"/api/v1/nutrition/meals/{meal.get_json()['id']}").status_code == 200
    assert signed_in.get("/api/nutrition/day").get_json()["meals"] == []


def test_v1_errors_have_the_same_shape(signed_in):
    legacy = signed_in.delete("/api/nutrition/meals/999")
    versioned = signed_in.delete("/api/v1/nutrition/meals/999")

    same_answer(legacy, versioned)
    assert versioned.get_json()["code"] == "meal_not_found"


def test_cross_site_writes_are_blocked_on_v1_too(signed_in):
    response = signed_in.post("/api/v1/training/plans", json={"name": "x"}, headers={"Origin": "https://evil.example"})

    assert response.status_code == 403
    assert response.get_json()["code"] == "forbidden"


# --- The bot: signed endpoints and the Telegram session scope ----------------------------


def bot_post(client, path, payload):
    body = json.dumps(payload).encode()
    headers = sign_request(BOT_SECRET, "POST", path, body)
    return client.post(path, data=body, headers=headers, content_type="application/json")


@pytest.fixture
def bot_session(app, client, user):
    from flask import g

    app.config["TELEGRAM_BOT_API_SECRET"] = BOT_SECRET

    def forget_cached_user():
        g.pop("_login_user", None)

    app.before_request_funcs.setdefault(None, []).insert(0, forget_cached_user)
    db.session.add(TelegramIdentity(user_id=user.id, telegram_user_id=333))
    db.session.commit()
    return client


@pytest.mark.parametrize("login_path", ["/api/telegram/login", "/api/v1/telegram/login"])
def test_the_bot_signs_in_on_either_path(bot_session, login_path):
    response = bot_post(bot_session, login_path, {"telegram_user_id": 333})

    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_a_signature_for_one_path_does_not_work_on_the_other(bot_session):
    body = json.dumps({"telegram_user_id": 333}).encode()
    headers = sign_request(BOT_SECRET, "POST", "/api/telegram/login", body)

    response = bot_session.post("/api/v1/telegram/login", data=body, headers=headers, content_type="application/json")

    assert response.status_code == 401


def test_the_telegram_session_scope_is_the_same_on_v1(bot_session):
    bot_post(bot_session, "/api/telegram/login", {"telegram_user_id": 333})

    for path in ("/api/nutrition/day", "/api/training/exercises/recent"):
        same_answer(bot_session.get(path), bot_session.get(v1(path)))
        assert bot_session.get(v1(path)).status_code == 200, path

    for path in ("/api/dashboard/today", "/api/training/plans"):
        legacy, versioned = bot_session.get(path), bot_session.get(v1(path))
        same_answer(legacy, versioned)
        assert versioned.status_code == 403
        assert versioned.get_json()["code"] == "telegram_session_scope"


def test_unversioned_maps_v1_paths_back():
    assert unversioned("/api/v1/nutrition/day") == "/api/nutrition/day"
    assert unversioned("/api/nutrition/day") == "/api/nutrition/day"
    assert unversioned("/api/v10/nutrition") == "/api/v10/nutrition"
    assert unversioned("/dashboard/") == "/dashboard/"
