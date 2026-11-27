"""Regression tests for the fixes from the November 2026 audit."""

import pytest

PASSWORD = "password123"


def login(client, email="test@example.com", password=PASSWORD):
    return client.post("/auth/login", data={"email": email, "password": password})


# --- Emailed codes: a replayed session cookie brings no extra guesses ----------------


@pytest.fixture
def delete_code(client, user, monkeypatch):
    sent = {}
    monkeypatch.setattr(
        "web.app.routes.profile.delete_account_request.send_email_code",
        lambda email, code: sent.update(code=code),
    )
    login(client)
    assert client.post("/profile/delete/request").get_json()["status"] == "sent"
    return sent


def _confirm(client, code):
    return client.post("/profile/delete/confirm", json={"code": code}).get_json()["status"]


def test_replayed_cookie_gets_no_more_guesses_after_lockout(client, delete_code):
    # The cookie issued with the code: an attacker can send it again and again.
    cookie = client.get_cookie("session").value

    assert [_confirm(client, "000000") for _ in range(5)] == ["wrong"] * 5
    assert _confirm(client, "000000") == "expired"

    client.set_cookie("session", cookie)
    assert _confirm(client, "000000") == "expired"
    client.set_cookie("session", cookie)
    assert _confirm(client, delete_code["code"]) == "expired"  # even the real code


def test_a_new_code_after_a_lockout_works(client, delete_code):
    for _ in range(6):
        _confirm(client, "000000")

    assert client.post("/profile/delete/request").get_json()["status"] == "sent"
    assert _confirm(client, delete_code["code"]) == "ok"


# --- /consent?next= stays on the site ---------------------------------------------------


@pytest.mark.parametrize(
    "next_value",
    [
        "/%09/evil.example",
        "/%09%09/evil.example/x",
        "/%0a/evil.example",
        "/%0d%0aSet-Cookie:x=1",
        "/%5Cevil.example",
        "/%5C/evil.example",
        "//evil.example",
        "/%2F/evil.example",
        "https://evil.example",
        "/%00/evil.example",
    ],
)
def test_consent_next_never_leaves_the_site(client, user, next_value):
    login(client)

    response = client.get(f"/consent?next={next_value}")

    assert response.status_code == 302
    location = response.headers["Location"]
    assert location.startswith("/") and not location.startswith("//")
    assert "evil.example" not in location


def test_consent_next_keeps_a_local_path(client, user):
    login(client)

    response = client.get("/consent?next=/dashboard/")

    assert response.headers["Location"] == "/dashboard/"


# --- Login: an unknown email costs the same password hash check ----------------------


@pytest.mark.parametrize("email", ["nobody@example.com", "test@example.com"])
def test_login_always_checks_a_password_hash(client, user, monkeypatch, email):
    from werkzeug import security

    calls = []
    real = security.check_password_hash

    def counting(pwhash, password):
        calls.append(pwhash)
        return real(pwhash, password)

    monkeypatch.setattr(security, "check_password_hash", counting)
    monkeypatch.setattr("web.app.routes.auth.main.check_password_hash", counting)
    monkeypatch.setattr("backend.app.models.user.check_password_hash", counting)

    client.post("/auth/login", data={"email": email, "password": "wrong-password"})

    assert len(calls) == 1
