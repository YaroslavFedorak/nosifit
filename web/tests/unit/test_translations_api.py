"""Translations API: the JSON the web client loads for each namespace."""

import pytest

from web.app.i18n.locale import SUPPORTED_LOCALES, load_translation


@pytest.mark.parametrize("locale", SUPPORTED_LOCALES)
@pytest.mark.parametrize("namespace", ["common", "nutrition", "dashboard", "public"])
def test_each_locale_and_namespace_is_served_without_signing_in(client, locale, namespace):
    response = client.get(f"/api/i18n/{locale}/{namespace}")

    assert response.status_code == 200
    assert response.mimetype == "application/json"
    assert response.get_json() == load_translation(locale, namespace)
    assert response.get_json()  # every one of these has text


def test_missing_keys_fall_back_to_ukrainian(client):
    uk = client.get("/api/i18n/uk/common").get_json()
    en = client.get("/api/i18n/en/common").get_json()

    assert en != uk
    assert set(en) >= set(uk)


def test_an_unsupported_locale_gets_ukrainian(client):
    assert client.get("/api/i18n/de/common").get_json() == client.get("/api/i18n/uk/common").get_json()


def test_an_unknown_namespace_is_an_empty_object(client):
    response = client.get("/api/i18n/en/no_such_namespace")

    assert response.status_code == 200
    assert response.get_json() == {}


@pytest.mark.parametrize("namespace", ["..", "Common", "1common", "common.json", "a" * 42, "com-mon"])
def test_namespaces_that_could_reach_other_files_are_not_found(client, namespace):
    assert client.get(f"/api/i18n/uk/{namespace}").status_code == 404


def test_signed_in_users_get_the_same_translations(client, user):
    guest = client.get("/api/i18n/pl/nutrition").get_json()
    client.post("/auth/login", data={"email": user.email, "password": "password123"})

    assert client.get("/api/i18n/pl/nutrition").get_json() == guest
