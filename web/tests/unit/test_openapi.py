"""docs/openapi.json describes the API that is actually registered.

- the committed file is what ``python -m web.scripts.openapi`` builds now;
- its operations are exactly the /api/v1 routes;
- the authentication it states is what the API enforces;
- every documented response body validates against a real response;
- it carries no secret from the app's configuration.
"""

import json
import re
from pathlib import Path

import pytest

from api.openapi import SERVER_URL, build_spec
from api.openapi_docs import OPERATIONS
from backend.app.extensions import db
from backend.app.models.injury import Injury
from backend.app.models.recovery.habit import RecoveryHabit
from backend.app.models.telegram import TelegramIdentity
from backend.app.models.verification_code import VerificationCode
from backend.app.training.exercises.catalog import load_exercise_catalog
from backend.app.training.models.exercise import Exercise
from backend.app.utils.bot_signature import sign_request
from web.scripts.openapi import OUTPUT, render

BOT_SECRET = "openapi-contract-bot-secret-" + "x" * 32
VALUES = {"date": "2026-01-01", "date_string": "2026-01-01", "date_iso": "2026-01-01",
          "code": "4006381333931", "locale": "uk", "namespace": "common"}


@pytest.fixture
def spec(app):
    return build_spec(app)


def operations(spec):
    for path, item in spec["paths"].items():
        for method, operation in item.items():
            yield path, method.upper(), operation


def concrete(path):
    return SERVER_URL + re.sub(r"\{(\w+)\}", lambda m: VALUES.get(m.group(1), "1"), path)


# --- A minimal JSON Schema check (the subset the description uses) ---------------------


def resolve(spec, schema):
    while "$ref" in schema:
        node = spec
        for part in schema["$ref"].lstrip("#/").split("/"):
            node = node[part]
        schema = node
    return schema


def _is(kind, value):
    return {
        "null": value is None,
        "boolean": isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "string": isinstance(value, str),
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
    }[kind]


def validate(spec, schema, value, where="$"):
    schema = resolve(spec, schema)
    for part in schema.get("allOf", ()):
        validate(spec, part, value, where)
    kinds = schema.get("type")
    if kinds is not None:
        kinds = kinds if isinstance(kinds, list) else [kinds]
        assert any(_is(kind, value) for kind in kinds), f"{where}: {value!r} is not {kinds}"
    if "enum" in schema:
        assert value in schema["enum"], f"{where}: {value!r} not in {schema['enum']}"
    if isinstance(value, str) and "pattern" in schema:
        assert re.search(schema["pattern"], value), f"{where}: {value!r} !~ {schema['pattern']}"
    if isinstance(value, str) and schema.get("format") == "date":
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", value), f"{where}: {value!r} is not a date"
    if isinstance(value, dict):
        for key in schema.get("required", ()):
            assert key in value, f"{where}: missing {key!r}"
        for key, sub in schema.get("properties", {}).items():
            if key in value:
                validate(spec, sub, value[key], f"{where}.{key}")
    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            validate(spec, schema["items"], item, f"{where}[{index}]")


def test_the_validator_rejects_what_it_should(spec):
    with pytest.raises(AssertionError):
        validate(spec, {"$ref": "#/components/schemas/Status"}, {})
    with pytest.raises(AssertionError):
        validate(spec, {"$ref": "#/components/schemas/Error"}, {"code": "Not A Code", "message": "x", "error": "x"})
    with pytest.raises(AssertionError):
        validate(spec, {"type": "integer"}, True)


# --- The file and the routes --------------------------------------------------------------


def test_the_committed_description_is_up_to_date(app):
    assert OUTPUT.read_text(encoding="utf-8") == render(app), (
        "docs/openapi.json is out of date: run python -m web.scripts.openapi"
    )


def test_operations_are_exactly_the_v1_routes(app, spec):
    routes = {
        (re.sub(r"<(?:\w+:)?(\w+)>", r"{\1}", rule.rule[len(SERVER_URL):]), method)
        for rule in app.url_map.iter_rules()
        if rule.rule.startswith(SERVER_URL + "/")
        for method in rule.methods - {"HEAD", "OPTIONS"}
    }
    documented = {(path, method) for path, method, _ in operations(spec)}

    assert documented == routes
    assert len(documented) > 90


def test_documentation_only_names_endpoints_that_exist(app):
    assert set(OPERATIONS) <= set(app.view_functions)


def test_every_operation_documents_its_errors(spec):
    for path, method, operation in operations(spec):
        responses = operation["responses"]
        assert "500" in responses, (method, path)
        if operation["x-auth"] == "session":
            assert "401" in responses, (method, path)
        for code, response in responses.items():
            if code.startswith(("4", "5")):
                body = resolve(spec, response)["content"]["application/json"]["schema"]
                assert body == {"$ref": "#/components/schemas/Error"}


def test_no_secret_from_the_configuration_is_published(app):
    text = render(app)
    for key, value in app.config.items():
        if isinstance(value, str) and len(value) >= 8 and re.search("SECRET|KEY|PASSWORD|TOKEN", key):
            assert value not in text, key


# --- Authentication as documented -------------------------------------------------------


def test_the_documented_authentication_is_enforced(app, client, spec):
    app.config["TELEGRAM_BOT_API_SECRET"] = BOT_SECRET
    seen = set()
    for path, method, operation in operations(spec):
        auth = operation["x-auth"]
        seen.add(auth)
        response = getattr(client, method.lower())(concrete(path), json={})
        if auth == "session":
            assert response.status_code == 401, (method, path)
            assert response.get_json()["code"] == "authentication_required"
        elif auth == "bot":
            assert response.status_code == 401, (method, path)
            assert response.get_json()["code"] == "unauthorized"
        else:
            assert response.status_code != 401, (method, path)
    assert seen == {"session", "bot", "public"}


# --- Documented bodies against real responses ------------------------------------------


class Checker:
    def __init__(self, spec, client):
        self.spec = spec
        self.client = client
        self.checked = set()
        self.by_id = {op["operationId"]: (path, method, op) for path, method, op in operations(spec)}

    def call(self, operation_id, path=None, query=None, body=None, headers=None, raw=None):
        doc_path, method, operation = self.by_id[operation_id]
        url = path or concrete(doc_path)
        kwargs = {"headers": headers or {}, "query_string": query}
        if raw is not None:
            kwargs.update(data=raw, content_type="application/json")
        elif method != "GET":
            kwargs["json"] = body if body is not None else {}
        response = getattr(self.client, method.lower())(url, **kwargs)
        (status, documented), = [(c, r) for c, r in operation["responses"].items() if c.startswith("2")]
        assert str(response.status_code) == status, (operation_id, response.status_code, response.get_json())
        schema = documented["content"]["application/json"]["schema"]
        if schema:
            validate(self.spec, schema, response.get_json(), operation_id)
            self.checked.add(operation_id)
        return response.get_json()


def bot_call(checker, operation_id, payload):
    path = SERVER_URL + checker.by_id[operation_id][0]
    raw = json.dumps(payload).encode()
    return checker.call(operation_id, path=path, raw=raw, headers=sign_request(BOT_SECRET, "POST", path, raw))


def test_documented_responses_match_real_ones(app, client, user, spec, monkeypatch):
    from flask import g

    app.config["TELEGRAM_BOT_API_SECRET"] = BOT_SECRET
    app.config["PUBLIC_BASE_URL"] = "https://nosifit.example"

    def forget_cached_user():
        g.pop("_login_user", None)

    app.before_request_funcs.setdefault(None, []).insert(0, forget_cached_user)

    for item in load_exercise_catalog()[:5]:
        db.session.add(Exercise(**item))
    injury = Injury(name="Knee", description="Knee pain")
    db.session.add_all([injury, RecoveryHabit(slug="walk", name="Walk", points=5)])
    db.session.commit()

    check = Checker(spec, client)
    client.post("/auth/login", data={"email": user.email, "password": "password123"})

    check.call("i18n.get_translation")
    check.call("injury_api.list_injuries")
    check.call("injury_api.set_user_injuries", body={"injuries": [injury.id]})
    check.call("equipment_api.get_equipment")

    meal = check.call("nutrition_api.api_add_meal", body={"category": "lunch"})
    check.call("nutrition_api.api_add_item", body={"meal_id": meal["id"], "name": "Rice", "calories": 130,
                                                   "protein": 2.7, "fat": 0.3, "carbs": 28})
    check.call("nutrition_api.api_edit_meal", path=f"{SERVER_URL}/nutrition/meals/{meal['id']}", body={"category": "dinner"})
    check.call("nutrition_api.api_day")
    check.call("nutrition_api.api_today")
    check.call("nutrition_api.api_add_water", body={"amount": 0.5})
    check.call("nutrition_api.api_get_water")
    check.call("nutrition_api.api_update_weight", body={"weight": 70})
    check.call("nutrition_api.api_get_weight")
    client.post("/api/v1/nutrition/products", json={"name": "Oat bar", "kcal_per_100g": 400, "protein_per_100g": 10,
                                                   "fat_per_100g": 15, "carbs_per_100g": 60})
    found = check.call("nutrition_api.api_products", query={"q": "Oat"})
    assert found["products"], "the search should find the product just created"
    check.call("dashboard_api.today")
    heatmap = check.call("dashboard_api.heatmap")
    assert heatmap["days"], "the meal makes today a day with data"
    check.call("nutrition_api.api_delete_meal", path=f"{SERVER_URL}/nutrition/meals/{meal['id']}")

    plan = check.call("training_api.create_plan", body={"name": "Push", "is_active": True})
    check.call("training_api.plans")
    check.call("training_api.update_plan", path=f"{SERVER_URL}/training/plans/{plan['id']}", body={"name": "Pull"})
    check.call("training_api.delete_plan", path=f"{SERVER_URL}/training/plans/{plan['id']}")
    check.call("training_api.start_session", body={})
    check.call("training_api.strength_test", body={"pushups": 10, "squats": 20})
    check.call("training_api.today_logged_session")
    check.call("training_api.exercises")
    check.call("training_api.search_exercise_catalog", query={"q": "a"})
    check.call("training_api.heatmap")

    check.call("recovery.get_habits_list")
    check.call("recovery.get_snapshot", path=f"{SERVER_URL}/recovery/snapshot/{user.id}",
               query={"date": "2026-01-01"})

    # The Telegram bot: signed calls, its own session.
    from backend.app.services import telegram_auth as tg

    monkeypatch.setattr(tg, "send_telegram_registration_code", lambda email, code: None)
    bot_call(check, "telegram_api.link_token", {"telegram_user_id": 501, "via": "google"})
    bot_call(check, "telegram_api.register_start", {"telegram_user_id": 502, "email": "new@example.com"})
    code = VerificationCode.query.filter_by(email="new@example.com").one().code
    bot_call(check, "telegram_api.register_verify",
             {"telegram_user_id": 502, "email": "new@example.com", "code": code, "name": "New"})
    db.session.add(TelegramIdentity(user_id=user.id, telegram_user_id=503))
    db.session.commit()
    bot_call(check, "telegram_api.telegram_login", {"telegram_user_id": 503, "username": "alice_tg"})
    bot_call(check, "telegram_api.telegram_logout", {"telegram_user_id": 503})

    documented = {op for op, doc in OPERATIONS.items() if "response" in doc}
    assert check.checked == documented
