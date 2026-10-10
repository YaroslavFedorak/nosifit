"""Barcode lookup: validation, catalog → cache → Open Food Facts, import.

Open Food Facts is never contacted: ``requests.get`` in the client module is
replaced by ``FakeOFF``, which serves canned responses and counts calls.
"""

import json
import threading
import time
from datetime import date, datetime, timedelta

import pytest
import requests

from backend.app.extensions import db
from backend.app.models import BarcodeLookup, Meal, MealItem, Product, ProductName, User
from backend.app.services.nutrition import open_food_facts
from backend.app.services.nutrition.barcode import (
    InvalidBarcode,
    gs1_check_digit,
    looks_like_barcode,
    normalize_barcode,
)
from backend.app.services.nutrition.barcode_service import (
    import_barcode_product,
    normalize_external_product,
)
from backend.app.services.nutrition.item_service import add_item_service
from werkzeug.security import generate_password_hash


def gtin(body: str) -> str:
    return body + str(gs1_check_digit(body))


NUTELLA = gtin("301762401070")       # 13 digits
COLA = gtin("544900000099")
MISSING = gtin("482000000001")
OTHER = gtin("590000000001")
UPC_BODY = gtin("01234567890")       # 12-digit UPC-A


def off_product(**overrides):
    product = {
        "code": NUTELLA,
        "lang": "en",
        "product_name": "Hazelnut spread",
        "product_name_uk": "Горіхова паста",
        "brands": "Ferrero, Nutella",
        "quantity": "400 g",
        "product_quantity_unit": "g",
        "nutriments": {
            "energy-kcal_100g": 539,
            "proteins_100g": 6.3,
            "fat_100g": 30.9,
            "carbohydrates_100g": 57.5,
            "sugars_100g": 56.3,
            "saturated-fat_100g": 10.6,
            "salt_100g": 0.107,
            "fiber_100g": 0,
            "unrelated_100g": 99,
        },
        "image_url": "https://images.example/evil.jpg",
    }
    nutriments = overrides.pop("nutriments", None)
    product.update(overrides)
    if nutriments is not None:
        product["nutriments"] = nutriments
    return product


class FakeResponse:
    def __init__(self, status_code=200, body=None, raw=None):
        self.status_code = status_code
        self._raw = raw if raw is not None else json.dumps(body).encode()
        self.closed = False

    def iter_content(self, chunk_size=1):
        for start in range(0, len(self._raw), chunk_size):
            yield self._raw[start:start + chunk_size]

    def close(self):
        self.closed = True


class FakeOFF:
    """Stands in for ``requests.get`` inside the Open Food Facts client."""

    def __init__(self):
        self.calls = []
        self.answers = {}
        self.delay = 0.0
        self._lock = threading.Lock()

    def found(self, code, **product):
        self.answers[code] = lambda: FakeResponse(
            200, {"code": code, "status": 1, "product": off_product(code=code, **product)}
        )

    def missing(self, code, http_status=404):
        self.answers[code] = lambda: FakeResponse(
            http_status, {"code": code, "status": 0, "status_verbose": "product not found"}
        )

    def fail(self, code, exc=None, response=None):
        def answer():
            if exc is not None:
                raise exc
            return response
        self.answers[code] = answer

    def __call__(self, url, params=None, headers=None, timeout=None, allow_redirects=True, stream=False):
        with self._lock:
            self.calls.append({"url": url, "params": params, "headers": headers,
                               "timeout": timeout, "allow_redirects": allow_redirects})
        if self.delay:
            time.sleep(self.delay)
        code = url.rsplit("/", 1)[1]
        return self.answers[code]()

    def count(self, code=None):
        return len([c for c in self.calls if code is None or c["url"].endswith("/" + code)])


@pytest.fixture
def off(monkeypatch):
    fake = FakeOFF()
    monkeypatch.setattr(open_food_facts.requests, "get", fake)
    return fake


def login(client, email="test@example.com"):
    return client.post("/auth/login", data={"email": email, "password": "password123"})


def make_user(name):
    user = User(username=name, email=f"{name}@example.com", password=generate_password_hash("password123"))
    db.session.add(user)
    db.session.commit()
    return user


def catalog_product(barcode=None, kcal=100, verified=True, source_ref=None, data_source="ciqual_2020", owner=None):
    product = Product(
        source="user" if owner else "system",
        owner_user_id=owner,
        barcode=barcode,
        kcal_per_100g=kcal,
        protein_per_100g=10,
        fat_per_100g=5,
        carbs_per_100g=8,
        default_unit="g",
        grams_per_unit=1,
        liquid_ml_per_100g=0,
        verified=verified,
        data_source=data_source,
        source_ref=source_ref,
        normalized_name="мій сир" if owner else None,
    )
    db.session.add(product)
    db.session.flush()
    db.session.add(ProductName(product_id=product.id, locale="uk", name="Мій сир" if owner else "Сир"))
    db.session.commit()
    return product


def lookup(client, code, locale="uk"):
    return client.get(f"/api/nutrition/products/barcode/{code}?locale={locale}")


def do_import(client, code, **body):
    return client.post(f"/api/nutrition/products/barcode/{code}/import", json={"locale": "uk", **body})


# --- barcode format ------------------------------------------------------------------


def test_barcode_normalization():
    assert normalize_barcode(NUTELLA) == NUTELLA
    assert normalize_barcode(" " + NUTELLA[:1] + " " + NUTELLA[1:7] + "-" + NUTELLA[7:]) == NUTELLA
    # UPC-A and GTIN-14 with leading zeros are the same product as EAN-13.
    assert normalize_barcode(UPC_BODY) == "0" + UPC_BODY
    assert normalize_barcode("0" + NUTELLA) == NUTELLA
    assert normalize_barcode(gtin("9638507")) == gtin("9638507")  # EAN-8

    bad_check = NUTELLA[:-1] + str((int(NUTELLA[-1]) + 1) % 10)
    for raw in (bad_check, "12345", "30176240107OO", "1" * 40, "", None, 3017624010701):
        with pytest.raises(InvalidBarcode):
            normalize_barcode(raw)

    assert looks_like_barcode(NUTELLA)
    assert not looks_like_barcode("молоко")
    assert not looks_like_barcode("1234")


def test_invalid_barcode_is_rejected_without_external_request(app, client, user, off):
    login(client)
    response = lookup(client, "1234567890123")  # wrong check digit
    assert response.status_code == 400
    assert response.get_json()["code"] == "invalid_barcode"
    assert lookup(client, "abc").status_code == 400
    assert off.count() == 0


# --- lookup order ------------------------------------------------------------------------


def test_existing_catalog_product_is_returned_without_external_request(app, client, user, off):
    product = catalog_product(barcode=NUTELLA)
    login(client)

    body = lookup(client, NUTELLA).get_json()

    assert body["status"] == "found"
    assert body["source"] == "catalog"
    assert body["product"]["id"] == product.id
    assert off.count() == 0


def test_seeded_label_product_matches_by_source_ref(app, client, user, off):
    """The catalog's Open Food Facts label rows keep the barcode in source_ref."""
    product = catalog_product(barcode=None, source_ref=NUTELLA, data_source="open_food_facts")
    login(client)

    body = lookup(client, NUTELLA).get_json()
    assert body["product"]["id"] == product.id
    assert off.count() == 0

    response = do_import(client, NUTELLA)
    assert response.status_code == 200
    assert response.get_json()["product"]["id"] == product.id
    assert Product.query.count() == 1


def test_external_product_preview_and_cache(app, client, user, off):
    off.found(NUTELLA)
    login(client)

    body = lookup(client, NUTELLA).get_json()

    assert body["status"] == "found"
    assert body["source"] == "open_food_facts"
    preview = body["preview"]
    assert preview["name"] == "Горіхова паста"
    assert preview["brand"] == "Ferrero"
    assert preview["kcal_per_100g"] == 539
    assert preview["fiber_per_100g"] == 0  # a known zero stays zero
    assert preview["verified"] is False
    assert preview["data_source"] == "open_food_facts"
    assert preview["source_ref"] == NUTELLA
    assert preview["importable"] is True
    assert "Open Database License" in body["attribution"]
    # Nothing is imported by a lookup.
    assert Product.query.count() == 0

    # Request shape: fixed host, fields limited, identified, timeouts, no redirects.
    call = off.calls[0]
    assert call["url"] == f"https://world.openfoodfacts.org/api/v2/product/{NUTELLA}"
    assert "nutriments" in call["params"]["fields"]
    assert "image" not in call["params"]["fields"]
    assert call["headers"]["User-Agent"].startswith("NosiFit/")
    assert call["timeout"] and call["allow_redirects"] is False

    # The cached copy keeps only whitelisted fields.
    row = db.session.get(BarcodeLookup, NUTELLA)
    assert row.status == "found"
    assert "image_url" not in row.payload
    assert "unrelated_100g" not in row.payload["nutriments"]

    # Repeated lookups (any user, any locale) use the cache.
    assert lookup(client, NUTELLA, "en").get_json()["preview"]["name"] == "Hazelnut spread"
    assert off.count() == 1


def test_cached_data_is_validated_again(app, client, user, off):
    """A cache row cannot carry values past validation."""
    db.session.add(BarcodeLookup(
        barcode=NUTELLA, provider="open_food_facts", status="found",
        payload=off_product(nutriments={"energy-kcal_100g": 5000, "proteins_100g": 1,
                                        "fat_100g": 1, "carbohydrates_100g": 1}),
        fetched_at=datetime.utcnow(), expires_at=datetime.utcnow() + timedelta(days=1),
    ))
    db.session.commit()
    login(client)

    preview = lookup(client, NUTELLA).get_json()["preview"]
    assert preview["invalid"] == {"kcal_per_100g": "too_large"}
    assert preview["importable"] is False
    assert do_import(client, NUTELLA).status_code == 422
    assert off.count() == 0


def test_missing_product_is_cached_as_not_found_until_it_expires(app, client, user, off):
    off.missing(MISSING)
    login(client)

    assert lookup(client, MISSING).get_json()["status"] == "not_found"
    assert lookup(client, MISSING).get_json()["status"] == "not_found"
    assert off.count(MISSING) == 1

    row = db.session.get(BarcodeLookup, MISSING)
    assert row.status == "not_found"
    assert row.expires_at - row.fetched_at == timedelta(days=7)

    row.expires_at = datetime.utcnow() - timedelta(seconds=1)
    db.session.commit()
    off.found(MISSING)
    assert lookup(client, MISSING).get_json()["status"] == "found"
    assert off.count(MISSING) == 2

    assert do_import(client, MISSING).status_code == 201


def test_status_zero_with_http_200_is_not_found(app, client, user, off):
    off.missing(MISSING, http_status=200)
    login(client)
    assert lookup(client, MISSING).get_json()["status"] == "not_found"


@pytest.mark.parametrize(
    "failure",
    [
        {"exc": requests.Timeout()},
        {"exc": requests.ConnectionError()},
        {"response": FakeResponse(429, {"status": 0})},
        {"response": FakeResponse(503, raw=b"<html>busy</html>")},
        {"response": FakeResponse(500, {"status": 0})},
        {"response": FakeResponse(200, raw=b"<html>not json</html>")},
        {"response": FakeResponse(404, raw=b"<html>Not Found</html>")},
        {"response": FakeResponse(200, {"status": 1, "product": "oops"})},
        {"response": FakeResponse(302, raw=b"")},
        {"response": FakeResponse(200, raw=b"{" + b" " * (600 * 1024) + b"}")},
    ],
    ids=["timeout", "network", "429", "503", "500", "html", "html-404", "bad-product", "redirect", "too-large"],
)
def test_temporary_failures_are_not_cached(app, client, user, off, failure):
    off.fail(MISSING, **failure)
    login(client)

    response = lookup(client, MISSING)

    assert response.status_code == 503
    body = response.get_json()
    assert body["code"] == "lookup_unavailable"
    # No upstream detail reaches the user.
    assert "html" not in json.dumps(body).lower()
    assert response.headers["Retry-After"]
    assert db.session.get(BarcodeLookup, MISSING) is None

    # The next scan asks again instead of trusting a "not found".
    off.found(MISSING)
    assert lookup(client, MISSING).get_json()["status"] == "found"
    assert off.count(MISSING) == 2


def test_stale_answer_is_used_while_open_food_facts_is_down(app, client, user, off):
    off.found(NUTELLA)
    login(client)
    lookup(client, NUTELLA)
    row = db.session.get(BarcodeLookup, NUTELLA)
    row.expires_at = datetime.utcnow() - timedelta(days=1)
    db.session.commit()

    off.fail(NUTELLA, exc=requests.Timeout())
    body = lookup(client, NUTELLA).get_json()

    assert body["status"] == "found"
    assert body["stale"] is True
    assert body["preview"]["kcal_per_100g"] == 539


def test_outbound_budget_protects_open_food_facts(app, client, user, off):
    app.config["OFF_MAX_REQUESTS_PER_MINUTE"] = 1
    off.found(NUTELLA)
    off.found(COLA)
    login(client)

    assert lookup(client, NUTELLA).status_code == 200
    response = lookup(client, COLA)
    assert response.status_code == 503
    assert off.count(COLA) == 0
    # Already-known barcodes keep working.
    assert lookup(client, NUTELLA).status_code == 200


def test_disabled_or_misconfigured_open_food_facts(app, client, user, off):
    off.found(NUTELLA)
    login(client)
    app.config["OFF_BASE_URL"] = "https://evil.example.com"
    assert lookup(client, NUTELLA).status_code == 503
    app.config["OFF_BASE_URL"] = "https://world.openfoodfacts.org"
    app.config["OFF_ENABLED"] = False
    assert lookup(client, NUTELLA).status_code == 503
    assert off.count() == 0


def test_per_user_rate_limit(app, client, user, off):
    off.missing(MISSING)
    login(client)
    statuses = [lookup(client, MISSING).status_code for _ in range(31)]
    assert statuses[:30] == [200] * 30
    assert statuses[30] == 429


# --- normalization and validation ----------------------------------------------------------


def preview_of(**product):
    return normalize_external_product(off_product(**product), "uk")


def test_missing_optional_values_stay_unknown():
    preview = preview_of(nutriments={
        "energy-kcal_100g": 100, "proteins_100g": 3, "fat_100g": 1, "carbohydrates_100g": 18,
    })
    assert preview["importable"] is True
    for field in ("fiber_per_100g", "sugar_per_100g", "saturated_fat_per_100g", "salt_per_100g"):
        assert preview[field] is None
    assert set(preview["missing_optional"]) == {
        "fiber_per_100g", "sugar_per_100g", "saturated_fat_per_100g", "salt_per_100g",
    }


def test_missing_mandatory_values_block_import():
    preview = preview_of(nutriments={"energy-kcal_100g": 100, "fat_100g": 1})
    assert preview["missing"] == ["protein_per_100g", "carbs_per_100g"]
    assert preview["protein_per_100g"] is None  # not 0
    assert preview["complete"] is False
    assert preview["importable"] is False

    nameless = normalize_external_product(
        {"nutriments": off_product()["nutriments"]}, "uk"
    )
    assert nameless["missing"] == ["name"]
    assert nameless["importable"] is False


@pytest.mark.parametrize(
    "nutriments, field, reason",
    [
        ({"proteins_100g": 150}, "protein_per_100g", "too_large"),
        ({"fat_100g": -1}, "fat_per_100g", "negative"),
        ({"energy-kcal_100g": 1200}, "kcal_per_100g", "too_large"),
        ({"sugars_100g": 80}, "sugar_per_100g", "exceeds_carbs"),
        ({"saturated-fat_100g": 40}, "saturated_fat_per_100g", "exceeds_fat"),
        ({"proteins_100g": "abc"}, "protein_per_100g", "not_a_number"),
        ({"salt_100g": 120}, "salt_per_100g", "too_large"),
        ({"energy-kcal_100g": 10}, "kcal_per_100g", "inconsistent_with_macros"),
        ({"proteins_100g": 40, "fat_100g": 40, "carbohydrates_100g": 40}, "protein_per_100g", "macros_exceed_100g"),
    ],
)
def test_implausible_values_are_rejected_not_clamped(nutriments, field, reason):
    values = {**off_product()["nutriments"], **nutriments}
    preview = preview_of(nutriments=values)
    assert preview["invalid"][field] == reason
    assert preview[field] is None  # never a clamped number
    assert preview["importable"] is False


def test_rounding_tolerance_for_parts_of_a_whole():
    preview = preview_of(nutriments={
        "energy-kcal_100g": 20, "proteins_100g": 0, "fat_100g": 0,
        "carbohydrates_100g": 5.0, "sugars_100g": 5.3,
    })
    assert preview["invalid"] == {}
    assert preview["sugar_per_100g"] == 5.3


def test_per_serving_values_are_converted_with_the_label_serving_size():
    preview = preview_of(
        serving_size="30 g",
        serving_quantity=30,
        nutriments={
            "energy-kcal_serving": 120, "proteins_serving": 3,
            "fat_serving": 1.5, "carbohydrates_serving": 24, "sugars_serving": 6,
        },
    )
    assert preview["kcal_per_100g"] == 400
    assert preview["protein_per_100g"] == 10
    assert preview["carbs_per_100g"] == 80
    assert preview["sugar_per_100g"] == 20
    assert "converted_from_serving" in preview["warnings"]
    assert preview["importable"] is True


def test_per_serving_values_without_serving_size_are_missing():
    preview = preview_of(
        serving_size="1 bar",
        nutriments={"energy-kcal_serving": 120, "proteins_serving": 3,
                    "fat_serving": 1.5, "carbohydrates_serving": 24},
    )
    assert preview["kcal_per_100g"] is None
    assert "kcal_per_100g" in preview["missing"]
    assert preview["importable"] is False


def test_drinks_are_per_100_ml():
    preview = preview_of(
        quantity="1.5 l",
        product_quantity_unit="ml",
        nutriments={"energy-kcal_100g": 42, "proteins_100g": 0, "fat_100g": 0,
                    "carbohydrates_100g": 10.6, "sugars_100g": 10.6},
    )
    assert preview["basis"] == "100ml"
    assert preview["default_unit"] == "ml"
    assert preview["grams_per_unit"] == 1.0
    assert "per_100ml" in preview["warnings"]


def test_energy_from_kj_and_salt_from_sodium():
    preview = preview_of(nutriments={
        "energy-kj_100g": 418.4, "proteins_100g": 5, "fat_100g": 2,
        "carbohydrates_100g": 12, "sodium_100g": 0.4,
    })
    assert preview["kcal_per_100g"] == 100
    assert preview["salt_per_100g"] == 1.0
    assert {"energy_from_kj", "salt_from_sodium"} <= set(preview["warnings"])


def test_names_and_brand_are_cleaned():
    preview = preview_of(
        product_name_uk="  Сир\u0000  <b>твердий</b> " + "я" * 200,
        brands="  Бренд   один ,Другий",
    )
    assert len(preview["name"]) <= 120
    assert "\u0000" not in preview["name"]
    assert preview["brand"] == "Бренд один"


# --- import ---------------------------------------------------------------------------------


def test_import_creates_one_private_unverified_own_product(app, client, user, off):
    off.found(NUTELLA)
    login(client)

    response = do_import(client, NUTELLA, kcal_per_100g=1, verified=True, name="Hacked")
    assert response.status_code == 201
    body = response.get_json()
    assert body["created"] is True
    product = body["product"]
    # Values come from the server's lookup, never from the request body.
    assert product["kcal_per_100g"] == 539
    assert product["name"] == "Горіхова паста"
    assert product["verified"] is False
    assert product["source"] == "user"
    assert product["is_own"] is True
    assert product["data_source"] == "open_food_facts"
    assert product["source_ref"] == NUTELLA
    assert product["barcode"] == NUTELLA
    assert product["fiber_per_100g"] == 0

    row = db.session.get(Product, product["id"])
    assert row.owner_user_id == user.id
    assert [n.locale for n in row.names] == ["uk"]
    # The cached answer stays for other users.
    assert db.session.get(BarcodeLookup, NUTELLA) is not None

    # Again: the same product, nothing new, no request.
    again = do_import(client, NUTELLA)
    assert again.status_code == 200
    assert again.get_json()["product"]["id"] == product["id"]
    assert Product.query.count() == 1
    assert off.count() == 1

    # In "My products" and found by name.
    mine = client.get("/api/nutrition/products/mine").get_json()["products"]
    assert [p["id"] for p in mine] == [product["id"]]
    found = client.get("/api/nutrition/products?q=горіхова").get_json()["products"]
    assert [p["id"] for p in found] == [product["id"]]


def test_imported_product_stays_private_and_others_reuse_the_cache(app, client, user, off):
    off.found(NUTELLA)
    login(client)
    first = do_import(client, NUTELLA).get_json()["product"]["id"]
    client.get("/auth/logout")

    make_user("bob")
    login(client, "bob@example.com")
    body = lookup(client, NUTELLA).get_json()
    assert body["source"] == "open_food_facts"  # not the other user's copy
    assert client.get(f"/api/nutrition/products/{first}").status_code == 404
    second = do_import(client, NUTELLA).get_json()["product"]
    assert second["id"] != first and second["is_own"] is True
    assert off.count() == 1  # the cached answer served both


def test_import_with_a_taken_name_adds_the_brand(app, client, user, off):
    off.found(NUTELLA)
    login(client)
    manual = {"kcal_per_100g": 1, "protein_per_100g": 0, "fat_per_100g": 0, "carbs_per_100g": 0}
    assert client.post("/api/nutrition/products", json={"name": "Горіхова паста", **manual}).status_code == 201

    product = do_import(client, NUTELLA).get_json()["product"]
    assert product["name"] == "Горіхова паста (Ferrero)"

    # Both names taken: a clear duplicate error, nothing created.
    db.session.delete(db.session.get(Product, product["id"]))
    db.session.commit()
    assert client.post("/api/nutrition/products", json={"name": "Горіхова паста (Ferrero)", **manual}).status_code == 201
    response = do_import(client, NUTELLA)
    assert response.status_code == 409
    assert response.get_json()["code"] == "duplicate_product"


def test_import_of_incomplete_or_missing_product_is_refused(app, client, user, off):
    off.found(NUTELLA, nutriments={"energy-kcal_100g": 539})
    off.missing(MISSING)
    login(client)

    response = do_import(client, NUTELLA)
    assert response.status_code == 422
    assert response.get_json()["code"] == "incomplete_product"
    assert do_import(client, MISSING).status_code == 404
    assert Product.query.count() == 0


def test_existing_verified_product_is_never_overwritten(app, client, user, off):
    product = catalog_product(barcode=NUTELLA, kcal=530, verified=True)
    off.found(NUTELLA)
    login(client)

    response = do_import(client, NUTELLA)

    assert response.status_code == 200
    assert response.get_json()["created"] is False
    db.session.refresh(product)
    assert product.kcal_per_100g == 530
    assert product.verified is True
    assert off.count() == 0


def test_archived_catalog_barcode_is_not_reimported(app, client, user, off):
    product = catalog_product(barcode=NUTELLA)
    product.is_active = False
    db.session.commit()
    off.found(NUTELLA)
    login(client)

    assert lookup(client, NUTELLA).get_json()["status"] == "not_found"
    assert do_import(client, NUTELLA).status_code == 404
    assert off.count() == 0


def test_own_product_with_barcode_stays_private(app, client, user, off):
    login(client)
    response = client.post("/api/nutrition/products", json={
        "name": "Мій сир", "barcode": NUTELLA, "kcal_per_100g": 300,
        "protein_per_100g": 20, "fat_per_100g": 25, "carbs_per_100g": 1,
    })
    assert response.status_code == 201
    own = response.get_json()
    assert own["barcode"] == NUTELLA

    # The owner finds their own product first.
    body = lookup(client, NUTELLA).get_json()
    assert body["product"]["id"] == own["id"]
    assert body["product"]["is_own"] is True

    # One barcode per user.
    duplicate = client.post("/api/nutrition/products", json={
        "name": "Інший сир", "barcode": NUTELLA, "kcal_per_100g": 1,
        "protein_per_100g": 0, "fat_per_100g": 0, "carbs_per_100g": 0,
    })
    assert duplicate.status_code == 409
    assert duplicate.get_json()["code"] == "duplicate_barcode"
    invalid = client.post("/api/nutrition/products", json={
        "name": "Ще сир", "barcode": "123", "kcal_per_100g": 1,
        "protein_per_100g": 0, "fat_per_100g": 0, "carbs_per_100g": 0,
    })
    assert invalid.status_code == 400
    assert invalid.get_json()["code"] == "invalid_barcode"
    client.get("/auth/logout")

    # Another user never sees it: they get the external data and can import
    # their own copy without clashing with the private product.
    off.found(NUTELLA)
    make_user("bob")
    login(client, "bob@example.com")
    body = lookup(client, NUTELLA).get_json()
    assert body["source"] == "open_food_facts"
    imported = do_import(client, NUTELLA)
    assert imported.status_code == 201
    assert imported.get_json()["product"]["id"] != own["id"]
    assert client.get(f"/api/nutrition/products/{own['id']}").status_code == 404


def test_concurrent_imports_by_one_user_create_one_product(app, user, off):
    """A double tap (two requests at once) gives one product, one request."""
    user_id = user.id
    off.found(NUTELLA)
    off.delay = 0.3
    results, errors = [], []
    start = threading.Barrier(2)

    def run():
        with app.app_context():
            try:
                start.wait()
                product, created = import_barcode_product(user_id, NUTELLA)
                results.append((product["id"], created))
            except Exception as exc:  # pragma: no cover - reported below
                errors.append(exc)
            finally:
                db.session.remove()

    threads = [threading.Thread(target=run) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(30)

    assert errors == []
    assert len({product_id for product_id, _ in results}) == 1
    assert sorted(created for _, created in results) == [False, True]
    assert off.count() == 1
    assert Product.query.filter_by(barcode=NUTELLA).count() == 1


def test_concurrent_lookups_by_two_users_make_one_request(app, off):
    user_ids = [make_user(f"user{i}").id for i in range(2)]
    off.found(NUTELLA)
    off.delay = 0.3
    errors = []
    start = threading.Barrier(2)

    def run(user_id):
        with app.app_context():
            try:
                start.wait()
                import_barcode_product(user_id, NUTELLA)
            except Exception as exc:  # pragma: no cover - reported below
                errors.append(exc)
            finally:
                db.session.remove()

    threads = [threading.Thread(target=run, args=(uid,)) for uid in user_ids]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(30)

    assert errors == []
    assert off.count() == 1
    assert Product.query.filter_by(barcode=NUTELLA).count() == 2  # one each


def test_imported_product_can_be_logged_and_history_stays_unchanged(app, client, user, off):
    off.found(NUTELLA)
    login(client)
    product = do_import(client, NUTELLA).get_json()["product"]

    response = client.post("/api/nutrition/log", json={
        "category": "breakfast",
        "items": [{"product_id": product["id"], "amount": 20, "unit": "g"}],
    })
    assert response.status_code == 201
    entry = MealItem.query.one()
    assert entry.calories == round(539 * 0.2)
    assert entry.fiber == 0
    assert entry.basis["kcal_per_100g"] == 539

    # Wrong community data can be corrected by the user...
    response = client.patch(f"/api/nutrition/products/{product['id']}", json={"kcal_per_100g": 100})
    assert response.status_code == 200
    assert response.get_json()["kcal_per_100g"] == 100
    # ...and the correction leaves the logged entry alone.
    db.session.expire_all()
    assert MealItem.query.one().calories == round(539 * 0.2)
    # Deleting archives it; history still stands.
    assert client.delete(f"/api/nutrition/products/{product['id']}").status_code == 200
    db.session.expire_all()
    assert MealItem.query.one().calories == round(539 * 0.2)


def test_unknown_optional_values_stay_unknown_in_logged_entries(app, user, off):
    off.found(COLA, nutriments={"energy-kcal_100g": 42, "proteins_100g": 0,
                                "fat_100g": 0, "carbohydrates_100g": 10.6},
               quantity="330 ml", product_quantity_unit="ml")
    product, _ = import_barcode_product(user.id, COLA)
    assert product["default_unit"] == "ml"
    assert product["sugar_per_100g"] is None

    meal = Meal(user_id=user.id, date=date.today(), name="snack", category="snack")
    db.session.add(meal)
    db.session.commit()
    entry = add_item_service(user.id, {
        "meal_id": meal.id, "product_id": product["id"], "amount": 330, "unit": "ml",
    })
    assert entry.calories == round(42 * 3.3)
    assert entry.sugar is None
    assert entry.fiber is None


def test_barcode_endpoints_require_login(app, client, off):
    off.found(NUTELLA)
    for response in (lookup(client, NUTELLA), do_import(client, NUTELLA)):
        assert response.status_code in (302, 401)
    assert off.count() == 0
    assert Product.query.count() == 0


def test_expired_cache_rows_are_purged(app, user, off):
    old = datetime.utcnow() - timedelta(days=90)
    db.session.add(BarcodeLookup(barcode=OTHER, provider="open_food_facts", status="not_found",
                                 fetched_at=old, expires_at=old))
    db.session.commit()
    off.missing(MISSING)
    from backend.app.services.nutrition.barcode_service import lookup_barcode

    lookup_barcode(user.id, MISSING)
    assert db.session.get(BarcodeLookup, OTHER) is None


def test_camera_and_wasm_are_allowed_only_on_pages_with_the_scanner(app, client, user):
    login(client)
    page = client.get("/nutrition/")
    assert page.status_code == 200
    assert "camera=(self)" in page.headers["Permissions-Policy"]
    assert "'wasm-unsafe-eval'" in page.headers["Content-Security-Policy"]
    assert "'unsafe-eval'" not in page.headers["Content-Security-Policy"].replace("'wasm-unsafe-eval'", "")
    assert b'id="open-barcode-scanner"' in page.data

    api = client.get("/api/nutrition/day")
    assert "camera=()" in api.headers["Permissions-Policy"]
    assert "wasm-unsafe-eval" not in api.headers["Content-Security-Policy"]


def test_vendored_decoder_is_served_locally(app, client):
    wasm = client.get("/static/vendor/zxing-wasm-3.1.4/zxing_reader.wasm")
    assert wasm.status_code == 200
    assert wasm.mimetype == "application/wasm"
    assert client.get("/static/vendor/zxing-wasm-3.1.4/zxing-reader.iife.js").status_code == 200


def test_ml_serving_on_a_product_sold_by_weight_is_not_a_drink():
    """Package in grams, serving in ml: per 100 g, and the ml serving is not
    turned into grams (that would need the unknown density)."""
    preview = preview_of(
        quantity="500 g",
        product_quantity_unit="g",
        serving_size="250 ml",
        serving_quantity=250,
        serving_quantity_unit="ml",
        nutriments={
            "energy-kcal_100g": 60, "proteins_100g": 3, "fat_100g": 1.5,
            "carbohydrates_100g": 8, "sugars_serving": 20,
        },
    )
    assert preview["basis"] == "100g"
    assert preview["default_unit"] == "g"
    assert "per_100ml" not in preview["warnings"]
    assert preview["sugar_per_100g"] is None  # not 20 * 100 / 250
    assert "converted_from_serving" not in preview["warnings"]

    # No package evidence at all, only an ml serving: flagged, not guessed.
    unclear = preview_of(
        quantity="", product_quantity_unit="", serving_quantity_unit="ml",
        nutriments={"energy-kcal_100g": 40, "proteins_100g": 0,
                    "fat_100g": 0, "carbohydrates_100g": 10},
    )
    assert unclear["default_unit"] == "g"
    assert "basis_uncertain" in unclear["warnings"]
    assert "per_100ml" not in unclear["warnings"]


def test_numeric_strings_from_open_food_facts_are_parsed(app, client, user, off):
    """Real responses often carry numbers as strings; blanks stay unknown."""
    off.answers[NUTELLA] = lambda: FakeResponse(200, {"status": 1, "product": {
        "product_name_uk": "Батончик",
        "product_quantity_unit": "g",
        "serving_size": "40 g",
        "serving_quantity": "40",
        "nutriments": {
            "energy-kcal_serving": "180", "proteins_serving": "4",
            "fat_serving": "6,4", "carbohydrates_100g": "62.5",
            "fiber_100g": "", "salt_100g": None,
        },
    }})
    login(client)

    preview = lookup(client, NUTELLA).get_json()["preview"]

    assert preview["kcal_per_100g"] == 450
    assert preview["protein_per_100g"] == 10
    assert preview["fat_per_100g"] == 16
    assert preview["carbs_per_100g"] == 62.5
    assert preview["fiber_per_100g"] is None and preview["salt_per_100g"] is None
    assert preview["invalid"] == {}
    assert preview["importable"] is True
