"""Nutrition API routes that the other nutrition tests do not reach.

test_nutrition_api, _dishes, _products, _search and _barcode cover the
catalog, dishes and barcode flows; test_critical_flows covers logging a
meal, water and weight. This file covers access, editing and deleting meals
and entries, the day and heatmap views and the 429 answer.
"""

import datetime as dt
import re

import pytest

ITEM = {"name": "Rice", "calories": 130, "protein": 2.7, "fat": 0.3, "carbs": 28}


@pytest.fixture
def signed_in(client, user):
    client.post("/auth/login", data={"email": user.email, "password": "password123"})
    return client


def nutrition_rules(app):
    return sorted(
        (rule.rule, sorted(rule.methods - {"HEAD", "OPTIONS"}))
        for rule in app.url_map.iter_rules()
        if rule.rule.startswith("/api/nutrition/")
    )


def test_every_nutrition_route_requires_signing_in(app, client):
    rules = nutrition_rules(app)
    assert len(rules) == 38

    values = {"date_string": "2026-01-01", "code": "4006381333931"}
    for rule, methods in rules:
        path = re.sub(r"<(?:int:)?(\w+)>", lambda m: values.get(m.group(1), "1"), rule)
        for method in methods:
            response = getattr(client, method.lower())(path, json={})
            assert response.status_code == 302, (method, path)
            assert "/auth/login" in response.headers["Location"]


def test_a_meal_and_its_entries_can_be_edited_and_deleted(signed_in):
    meal = signed_in.post("/api/nutrition/meals", json={"category": "lunch"}).get_json()
    item_id = signed_in.post("/api/nutrition/items", json={"meal_id": meal["id"], **ITEM}).get_json()["id"]

    renamed = signed_in.put(f"/api/nutrition/meals/{meal['id']}", json={"category": "dinner"})
    assert renamed.status_code == 200
    assert renamed.get_json()["category"] == "dinner"

    bad_category = signed_in.put(f"/api/nutrition/meals/{meal['id']}", json={"category": "brunch-ish"})
    assert bad_category.status_code == 400
    assert bad_category.get_json()["code"] == "invalid_category"

    edited = signed_in.put(f"/api/nutrition/items/{item_id}", json={"amount": 200})
    assert edited.status_code == 200
    assert edited.get_json() == {"id": item_id, "status": "ok"}
    assert signed_in.get("/api/nutrition/day").get_json()["kcal"] == pytest.approx(260, abs=1)

    assert signed_in.delete(f"/api/nutrition/entries/{item_id}").get_json() == {"status": "ok"}
    assert signed_in.get("/api/nutrition/day").get_json()["kcal"] == 0

    assert signed_in.delete(f"/api/nutrition/meals/{meal['id']}").get_json() == {"status": "ok"}
    assert signed_in.get("/api/nutrition/day").get_json()["meals"] == []

    missing = signed_in.delete(f"/api/nutrition/meals/{meal['id']}")
    assert missing.status_code == 404
    assert missing.get_json() == {"error": "Meal not found"}


def test_day_views_and_heatmap(signed_in):
    meal = signed_in.post("/api/nutrition/meals", json={"category": "lunch"}).get_json()
    signed_in.post("/api/nutrition/items", json={"meal_id": meal["id"], **ITEM})
    today = dt.date.today().isoformat()

    assert signed_in.get("/api/nutrition/today").get_json()["kcal"] == pytest.approx(130, abs=1)
    details = signed_in.get(f"/api/nutrition/day/{today}")
    assert details.status_code == 200
    assert signed_in.get("/api/nutrition/day/not-a-date").status_code == 400

    heatmap = signed_in.get("/api/nutrition/heatmap", query_string={"year": dt.date.today().year})
    assert heatmap.status_code == 200
    out_of_range = signed_in.get("/api/nutrition/heatmap", query_string={"year": 1999})
    assert out_of_range.status_code == 400
    assert out_of_range.get_json()["code"] == "invalid_year"
    # A year that is not a number falls back to this year (existing behaviour).
    assert signed_in.get("/api/nutrition/heatmap", query_string={"year": "abc"}).get_json() == heatmap.get_json()


def test_rate_limited_barcode_lookups_answer_429_json(app, signed_in, monkeypatch):
    import sys

    module = sys.modules[app.view_functions["nutrition_api.api_barcode_lookup"].__module__]
    monkeypatch.setattr(module, "hit_limit", lambda *args: True)

    for response in (
        signed_in.get("/api/nutrition/products/barcode/4006381333931"),
        signed_in.post("/api/nutrition/products/barcode/4006381333931/import", json={}),
    ):
        assert response.status_code == 429
        assert response.get_json() == {"error": "Too many requests. Try again later.", "code": "rate_limited"}
