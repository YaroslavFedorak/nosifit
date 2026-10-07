"""Telegram as an independent sign-in identity.

Written from an attacker's point of view where it matters: the attacker can
craft any HTTP request, owns their own Telegram and NosiFit accounts, may
have stolen a session or a link, but does not know TELEGRAM_BOT_API_SECRET.
"""

import json
import re
import time
from datetime import datetime, timedelta, timezone

import pytest
from werkzeug.security import generate_password_hash

from backend.app.extensions import db
from backend.app.models.oauth_account import OAuthAccount
from backend.app.models.telegram import TelegramIdentity, TelegramLinkToken
from backend.app.models.user import OAUTH_PASSWORD_MARKER, User
from backend.app.models.verification_code import VerificationCode
from backend.app.services import telegram_auth as tg
from backend.app.services.account_service import delete_user_account
from backend.app.utils.bot_signature import (
    HEADER_NONCE,
    HEADER_SIGNATURE,
    HEADER_TIMESTAMP,
    compute_signature,
    sign_request,
)
from backend.app.utils.session_auth import make_session_id

SECRET = "test-bot-secret-" + "x" * 40
PASSWORD = "password123"
TG_ALICE = 111_000_111
TG_MALLORY = 666_000_666


# --- Helpers ----------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def telegram_enabled(app):
    app.config["TELEGRAM_BOT_API_SECRET"] = SECRET
    app.config["PUBLIC_BASE_URL"] = "http://localhost"


@pytest.fixture(autouse=True)
def per_request_user(app):
    """conftest keeps one app context (and so one ``g``) for the whole test;
    Flask-Login caches the user in ``g``. Production loads the user from each
    request's own cookie, and so must these tests (several clients, sessions
    that are revoked between requests)."""
    from flask import g

    def forget_cached_user():
        g.pop("_login_user", None)

    app.before_request_funcs.setdefault(None, []).insert(0, forget_cached_user)


@pytest.fixture
def mail(monkeypatch):
    sent = []

    def fake_send(to, subject, text, html=None):
        sent.append({"to": to, "subject": subject, "text": text})

    monkeypatch.setattr("backend.app.services.telegram_auth.send_email", fake_send)
    monkeypatch.setattr(
        "web.app.routes.profile.connected_accounts.send_email_code",
        lambda email, code: sent.append({"to": email, "code": code, "text": code}),
    )
    return sent


def bot_post(client, path, payload, secret=SECRET, headers=None, raw_body=None):
    body = raw_body if raw_body is not None else json.dumps(payload).encode()
    signed = sign_request(secret, "POST", path, body)
    signed.update(headers or {})
    return client.post(path, data=body, headers=signed, content_type="application/json")


def tg_payload(tg_id=TG_ALICE, **extra):
    return {"telegram_user_id": tg_id, "username": "alice_tg", "name": "Alice", **extra}


def web_login(client, email="test@example.com", password=PASSWORD):
    return client.post("/auth/login", data={"email": email, "password": password})


def make_user(email, password=PASSWORD, username="u"):
    user = User(
        username=username,
        email=email,
        password=generate_password_hash(password) if password else OAUTH_PASSWORD_MARKER,
    )
    db.session.add(user)
    db.session.commit()
    return user


def link(user, tg_id, username=None):
    identity = TelegramIdentity(user_id=user.id, telegram_user_id=tg_id, telegram_username=username)
    db.session.add(identity)
    db.session.commit()
    return identity


def browser_session_for(client, user):
    """A signed-in browser session without a password (OAuth-style)."""
    with client.session_transaction() as session:
        session["_user_id"] = make_session_id(user)
        session["_fresh"] = True


def register(client, mail, email="new@example.com", tg_id=TG_ALICE):
    assert bot_post(client, "/api/telegram/register/start", tg_payload(tg_id, email=email)).status_code == 200
    code = VerificationCode.query.filter_by(email=email).first().code
    return bot_post(client, "/api/telegram/register/verify", tg_payload(tg_id, email=email, code=code))


def request_link(client, tg_id=TG_ALICE, username="alice_tg", name="Alice"):
    response = bot_post(
        client,
        "/api/telegram/link-token",
        {"telegram_user_id": tg_id, "username": username, "name": name},
    )
    assert response.status_code == 200, response.json
    url = response.json["url"]
    return url[len("http://localhost"):], url.rsplit("/", 1)[1]


def pending_csrf(client):
    with client.session_transaction() as session:
        return session["tg_link"]["csrf"]


# --- Request signatures (the bot is the only party that may name a Telegram id) ---------


def test_unsigned_request_is_rejected(client):
    response = client.post("/api/telegram/login", json=tg_payload())
    assert response.status_code == 401
    assert "Set-Cookie" not in response.headers


def test_wrong_secret_is_rejected(client, user):
    link(user, TG_ALICE)
    response = bot_post(client, "/api/telegram/login", tg_payload(), secret="w" * 48)
    assert response.status_code == 401


def test_replayed_request_is_rejected(client, user):
    link(user, TG_ALICE)
    body = json.dumps(tg_payload()).encode()
    headers = sign_request(SECRET, "POST", "/api/telegram/login", body)

    first = client.post("/api/telegram/login", data=body, headers=headers, content_type="application/json")
    replay = client.post("/api/telegram/login", data=body, headers=headers, content_type="application/json")

    assert first.status_code == 200
    assert replay.status_code == 401


def test_stale_signature_is_rejected(client, user):
    link(user, TG_ALICE)
    body = json.dumps(tg_payload()).encode()
    old = str(int(time.time()) - 600)
    nonce = "n" * 24
    headers = {
        HEADER_TIMESTAMP: old,
        HEADER_NONCE: nonce,
        HEADER_SIGNATURE: compute_signature(SECRET, old, nonce, "POST", "/api/telegram/login", body),
    }
    response = client.post("/api/telegram/login", data=body, headers=headers, content_type="application/json")
    assert response.status_code == 401


def test_telegram_id_substitution_breaks_signature(client, user, victim_identity):
    """Signed for Mallory's id, body swapped to the victim's id."""
    signed_body = json.dumps(tg_payload(TG_MALLORY)).encode()
    headers = sign_request(SECRET, "POST", "/api/telegram/login", signed_body)
    forged = json.dumps(tg_payload(TG_ALICE)).encode()

    response = client.post("/api/telegram/login", data=forged, headers=headers, content_type="application/json")

    assert response.status_code == 401


def test_signature_is_bound_to_the_path(client, user):
    link(user, TG_ALICE)
    body = json.dumps(tg_payload()).encode()
    headers = sign_request(SECRET, "POST", "/api/telegram/link-token", body)
    response = client.post("/api/telegram/login", data=body, headers=headers, content_type="application/json")
    assert response.status_code == 401


def test_feature_is_off_without_secret(client, app, user):
    app.config["TELEGRAM_BOT_API_SECRET"] = None
    link(user, TG_ALICE)
    assert bot_post(client, "/api/telegram/login", tg_payload()).status_code == 404


def test_short_bot_secret_refuses_to_start():
    from web.app.security import check_telegram_config

    with pytest.raises(RuntimeError, match="TELEGRAM_BOT_API_SECRET"):
        check_telegram_config({"TELEGRAM_BOT_API_SECRET": "short"})
    check_telegram_config({"TELEGRAM_BOT_API_SECRET": None})


@pytest.mark.parametrize(
    "bad_id",
    [None, "abc", True, -5, 0, 1.5, 2**64, "1" * 40, "12 34", [1], {"id": 1}],
)
def test_malformed_telegram_ids_are_rejected(client, bad_id):
    response = bot_post(client, "/api/telegram/login", {"telegram_user_id": bad_id})
    assert response.status_code == 400


def test_non_json_and_huge_bodies_are_rejected(client):
    assert bot_post(client, "/api/telegram/login", None, raw_body=b"not json").status_code == 400
    huge = json.dumps({"telegram_user_id": TG_ALICE, "name": "x" * 10_000}).encode()
    assert bot_post(client, "/api/telegram/login", None, raw_body=huge).status_code == 413


def test_redis_outage_fails_closed(client, app, user):
    link(user, TG_ALICE)
    app.config["RATELIMIT_REDIS_URL"] = "redis://127.0.0.1:1/0"
    app.extensions.pop("nosifit_ratelimit", None)

    response = bot_post(client, "/api/telegram/login", tg_payload())

    assert response.status_code == 503
    assert "Set-Cookie" not in response.headers


# --- Registration through the bot ---------------------------------------------------------


@pytest.fixture
def victim_identity(app):
    victim = make_user("victim@example.com", username="victim")
    return link(victim, TG_ALICE, "alice_tg")


def test_new_telegram_user_creates_account_without_password(client, mail):
    response = register(client, mail)

    assert response.status_code == 201
    user = User.query.filter_by(email="new@example.com").one()
    assert not user.has_password
    assert user.profile is not None
    identity = TelegramIdentity.query.filter_by(user_id=user.id).one()
    assert identity.telegram_user_id == TG_ALICE
    assert identity.telegram_username == "alice_tg"
    # The code went to the address, nowhere else; it is spent.
    assert mail[0]["to"] == "new@example.com" and re.search(r"\b\d{6}\b", mail[0]["text"])
    assert VerificationCode.query.count() == 0
    # Signed in right away, without a remember-me cookie.
    assert "remember_token" not in " ".join(response.headers.getlist("Set-Cookie"))
    assert client.get("/api/nutrition/water").status_code == 200


def test_registration_rejects_wrong_code(client, mail):
    bot_post(client, "/api/telegram/register/start", tg_payload(email="new@example.com"))
    real = VerificationCode.query.one().code
    wrong = "000000" if real != "000000" else "111111"

    response = bot_post(
        client, "/api/telegram/register/verify", tg_payload(email="new@example.com", code=wrong)
    )

    assert response.status_code == 400 and response.json["code"] == "invalid_code"
    assert User.query.count() == 0


def test_registration_rejects_expired_code(client, mail):
    bot_post(client, "/api/telegram/register/start", tg_payload(email="new@example.com"))
    record = VerificationCode.query.one()
    record.created_at = datetime.now(timezone.utc) - timedelta(minutes=11)
    db.session.commit()

    response = bot_post(
        client, "/api/telegram/register/verify", tg_payload(email="new@example.com", code=record.code)
    )

    assert response.json["code"] == "invalid_code"
    assert User.query.count() == 0


def test_registration_code_is_single_use(client, mail):
    bot_post(client, "/api/telegram/register/start", tg_payload(email="new@example.com"))
    code = VerificationCode.query.one().code
    assert bot_post(
        client, "/api/telegram/register/verify", tg_payload(email="new@example.com", code=code)
    ).status_code == 201

    replay = bot_post(
        client,
        "/api/telegram/register/verify",
        tg_payload(TG_MALLORY, email="new@example.com", code=code),
    )

    assert replay.status_code in (400, 409)
    assert TelegramIdentity.query.filter_by(telegram_user_id=TG_MALLORY).count() == 0


def test_registration_code_brute_force_is_capped(client, mail):
    bot_post(client, "/api/telegram/register/start", tg_payload(email="new@example.com"))
    code = VerificationCode.query.one().code
    wrong = [c for c in ("000000", "111111", "222222", "333333", "444444", "555555", "666666") if c != code]

    statuses = [
        bot_post(
            client, "/api/telegram/register/verify", tg_payload(email="new@example.com", code=c)
        ).status_code
        for c in wrong[:6]
    ]
    late = bot_post(client, "/api/telegram/register/verify", tg_payload(email="new@example.com", code=code))

    assert statuses[:5] == [400] * 5 and statuses[5] == 429
    assert late.status_code == 429  # the code is gone after too many tries
    assert User.query.count() == 0


def test_brute_force_spread_over_telegram_accounts_shares_the_email_counter(client, mail):
    bot_post(client, "/api/telegram/register/start", tg_payload(email="new@example.com"))
    code = VerificationCode.query.one().code
    wrong = "000000" if code != "000000" else "111111"

    for i in range(5):
        bot_post(
            client, "/api/telegram/register/verify", tg_payload(500 + i, email="new@example.com", code=wrong)
        )
    response = bot_post(
        client, "/api/telegram/register/verify", tg_payload(999, email="new@example.com", code=code)
    )

    assert response.status_code == 429
    assert User.query.count() == 0


def test_existing_email_is_not_enumerable_and_never_linked(client, mail, user):
    new = bot_post(client, "/api/telegram/register/start", tg_payload(TG_MALLORY, email="fresh@example.com"))
    existing = bot_post(client, "/api/telegram/register/start", tg_payload(TG_ALICE, email="test@example.com"))

    assert existing.status_code == new.status_code == 200
    assert existing.json == new.json
    # The owner gets an explanation, not a code.
    notice = [m for m in mail if m["to"] == "test@example.com"]
    assert len(notice) == 1 and not re.search(r"\b\d{6}\b", notice[0]["text"])
    assert VerificationCode.query.filter_by(email="test@example.com").count() == 0

    for code in ("123456", "000000"):
        attempt = bot_post(
            client, "/api/telegram/register/verify", tg_payload(TG_ALICE, email="test@example.com", code=code)
        )
        assert attempt.json["code"] == "invalid_code"
    assert TelegramIdentity.query.count() == 0


def test_email_registered_meanwhile_is_not_linked(client, mail):
    bot_post(client, "/api/telegram/register/start", tg_payload(email="race@example.com"))
    code = VerificationCode.query.one().code
    owner = make_user("race@example.com", username="owner")

    response = bot_post(
        client, "/api/telegram/register/verify", tg_payload(email="race@example.com", code=code)
    )

    assert response.status_code == 409 and response.json["code"] == "email_unavailable"
    assert TelegramIdentity.query.filter_by(user_id=owner.id).count() == 0


def test_linked_telegram_cannot_register_again(client, mail, victim_identity):
    start = bot_post(client, "/api/telegram/register/start", tg_payload(email="second@example.com"))
    verify = bot_post(
        client, "/api/telegram/register/verify", tg_payload(email="second@example.com", code="123456")
    )

    assert start.status_code == 409 and start.json["code"] == "already_linked"
    assert verify.status_code == 409
    assert User.query.filter_by(email="second@example.com").count() == 0


@pytest.mark.parametrize(
    "email",
    ["", "not-an-email", "a@b", "x" * 200 + "@example.com", "<script>@x.io", None, 12345, ["a@b.co"]],
)
def test_malformed_emails_are_rejected(client, mail, email):
    response = bot_post(client, "/api/telegram/register/start", tg_payload(email=email))
    assert response.status_code == 400
    assert mail == []


def test_registration_requests_are_limited_per_telegram_user(client, mail):
    statuses = [
        bot_post(client, "/api/telegram/register/start", tg_payload(email=f"r{i}@example.com")).status_code
        for i in range(6)
    ]
    assert statuses == [200] * 5 + [429]


def test_registration_display_name_is_sanitised(client, mail):
    payload = tg_payload(email="n@example.com", name="<img src=x onerror=alert(1)>‮\x00" + "y" * 200)
    bot_post(client, "/api/telegram/register/start", payload)
    code = VerificationCode.query.one().code
    bot_post(client, "/api/telegram/register/verify", {**payload, "code": code})

    user = User.query.filter_by(email="n@example.com").one()
    assert len(user.username) <= 50 and "\x00" not in user.username


# --- Login through the bot -------------------------------------------------------------------


def test_linked_telegram_logs_in(client, victim_identity):
    response = bot_post(client, "/api/telegram/login", tg_payload())

    assert response.status_code == 200
    assert client.get("/api/nutrition/water").status_code == 200
    assert TelegramIdentity.query.one().last_login_at is not None


def test_unknown_telegram_cannot_log_in(client, user):
    response = bot_post(client, "/api/telegram/login", tg_payload(TG_MALLORY))

    assert response.status_code == 404 and response.json["code"] == "not_linked"
    assert client.get("/api/nutrition/water").status_code in (302, 401)


def test_username_is_not_an_identity(client, victim_identity):
    """Mallory renames herself to the victim's @username: nothing changes."""
    response = bot_post(
        client, "/api/telegram/login", {"telegram_user_id": TG_MALLORY, "username": "alice_tg"}
    )
    assert response.status_code == 404

    # The victim renamed: still the victim; the stored username follows.
    renamed = bot_post(client, "/api/telegram/login", {"telegram_user_id": TG_ALICE, "username": "new_name"})
    assert renamed.status_code == 200
    assert TelegramIdentity.query.one().telegram_username == "new_name"


def test_deleted_account_cannot_log_in_and_its_bot_session_dies(client, app, mail):
    register(client, mail)
    user = User.query.filter_by(email="new@example.com").one()

    delete_user_account(user)

    assert TelegramIdentity.query.count() == 0
    assert client.get("/api/nutrition/water").status_code in (302, 401)
    assert bot_post(client, "/api/telegram/login", tg_payload()).json["code"] == "not_linked"


def test_concurrent_logins_get_independent_sessions(app, victim_identity):
    first, second = app.test_client(), app.test_client()
    assert bot_post(first, "/api/telegram/login", tg_payload()).status_code == 200
    assert bot_post(second, "/api/telegram/login", tg_payload()).status_code == 200
    assert first.get("/api/nutrition/water").status_code == 200
    assert second.get("/api/nutrition/water").status_code == 200


def test_login_is_rate_limited_per_telegram_user(client, victim_identity):
    statuses = [bot_post(client, "/api/telegram/login", tg_payload()).status_code for _ in range(21)]
    assert statuses[-1] == 429
    assert bot_post(client, "/api/telegram/login", tg_payload(TG_MALLORY)).status_code == 404


# --- Telegram session: same mechanism, narrower scope, revocable --------------------------


@pytest.mark.parametrize(
    "method, path, body",
    [
        ("post", "/profile/change_email", {"new_email": "mallory@example.com"}),
        ("post", "/profile/change_password", None),
        ("post", "/profile/delete/request", None),
        ("post", "/profile/telegram/disconnect", {}),
        ("post", "/profile/oauth_disconnect", None),
        ("post", "/auth/telegram/link/confirm", None),
        ("get", "/profile/", None),
        ("get", "/dashboard/", None),
    ],
)
def test_telegram_session_cannot_manage_the_account(client, victim_identity, method, path, body):
    bot_post(client, "/api/telegram/login", tg_payload())

    response = getattr(client, method)(path, json=body) if body is not None else getattr(client, method)(path)

    assert response.status_code == 403
    victim = User.query.filter_by(email="victim@example.com").one()
    assert victim.email == "victim@example.com"


def test_disconnecting_telegram_revokes_bot_sessions(client, victim_identity):
    bot_post(client, "/api/telegram/login", tg_payload())
    assert client.get("/api/nutrition/water").status_code == 200

    db.session.delete(victim_identity)
    db.session.commit()

    assert client.get("/api/nutrition/water").status_code == 401
    assert client.get("/api/nutrition/water").status_code in (302, 401)


def test_relinking_does_not_revive_old_bot_sessions(client, victim_identity):
    bot_post(client, "/api/telegram/login", tg_payload())
    victim = victim_identity.user
    db.session.delete(victim_identity)
    db.session.commit()
    link(victim, TG_ALICE)

    assert client.get("/api/nutrition/water").status_code == 401


def test_forged_telegram_marker_for_someone_elses_identity(client, user, victim_identity):
    """Mallory's own session claiming the victim's identity id is dropped."""
    web_login(client)
    with client.session_transaction() as session:
        session["tg_identity"] = victim_identity.id

    assert client.get("/api/nutrition/water").status_code == 401


def test_password_change_ends_bot_sessions(client, mail):
    register(client, mail)
    user = User.query.filter_by(email="new@example.com").one()
    user.set_password("a-new-password-1")
    db.session.commit()

    assert client.get("/api/nutrition/water").status_code in (302, 401)


# --- Linking an existing account -------------------------------------------------------------


def test_full_linking_flow_for_a_signed_out_user(client, user, mail):
    path, token = request_link(client)
    stored = TelegramLinkToken.query.one()
    assert stored.token_hash == tg.hash_link_token(token) and token not in stored.token_hash

    opened = client.get(path)
    assert opened.status_code == 302 and opened.location.endswith("/auth/telegram/link")
    assert opened.headers["Referrer-Policy"] == "no-referrer"
    assert client.get("/auth/telegram/link").location.endswith("/auth/login")

    logged_in = web_login(client)
    assert logged_in.location.endswith("/auth/telegram/link")

    page = client.get("/auth/telegram/link").get_data(as_text=True)
    assert "@alice_tg" in page and "test@example.com" in page
    assert TelegramIdentity.query.count() == 0  # nothing happens without Confirm

    confirmed = client.post("/auth/telegram/link/confirm", data={"csrf_token": pending_csrf(client)})

    assert confirmed.status_code == 200
    identity = TelegramIdentity.query.one()
    assert (identity.user_id, identity.telegram_user_id) == (user.id, TG_ALICE)
    assert any(m["to"] == "test@example.com" and "Telegram" in m["subject"] for m in mail)
    assert bot_post(app_client(client), "/api/telegram/login", tg_payload()).status_code == 200


def app_client(client):
    return client.application.test_client()


def test_confirmation_works_with_browser_origin_headers(client, user, mail):
    """Regression: a no-referrer policy on the confirmation page made Firefox
    send "Origin: null" with the form, which the CSRF check rejects."""
    web_login(client)
    path, _ = request_link(client)
    client.get(path)
    page = client.get("/auth/telegram/link")
    html = page.get_data(as_text=True)

    assert 'content="no-referrer"' not in html
    assert page.headers.get("Referrer-Policy") != "no-referrer"

    response = client.post(
        "/auth/telegram/link/confirm",
        data={"csrf_token": pending_csrf(client)},
        headers={"Origin": "http://localhost", "Referer": "http://localhost/auth/telegram/link"},
    )

    assert response.status_code == 200
    assert TelegramIdentity.query.count() == 1


def test_signed_in_user_sees_confirmation_first(client, user, mail):
    web_login(client)
    path, _ = request_link(client)

    client.get(path)
    page = client.get("/auth/telegram/link")

    assert page.status_code == 200 and "csrf_token" in page.get_data(as_text=True)
    assert TelegramIdentity.query.count() == 0


def test_expired_link_is_rejected(client, user, mail):
    web_login(client)
    path, _ = request_link(client)
    TelegramLinkToken.query.update({"expires_at": datetime.now(timezone.utc) - timedelta(seconds=1)})
    db.session.commit()

    assert client.get(path).status_code == 400
    with client.session_transaction() as session:
        assert "tg_link" not in session


def test_link_expiring_after_opening_cannot_be_confirmed(client, user, mail):
    web_login(client)
    path, _ = request_link(client)
    client.get(path)
    csrf = pending_csrf(client)
    TelegramLinkToken.query.update({"expires_at": datetime.now(timezone.utc) - timedelta(seconds=1)})
    db.session.commit()

    assert client.post("/auth/telegram/link/confirm", data={"csrf_token": csrf}).status_code == 400
    assert TelegramIdentity.query.count() == 0


def test_link_cannot_be_reused(app, user, mail):
    first = app.test_client()
    web_login(first)
    path, _ = request_link(first)
    first.get(path)
    first.post("/auth/telegram/link/confirm", data={"csrf_token": pending_csrf(first)})

    other = make_user("other@example.com")
    second = app.test_client()
    web_login(second, "other@example.com")

    assert second.get(path).status_code == 400
    assert first.get(path).status_code == 400
    assert TelegramIdentity.query.one().user_id == user.id
    assert other.telegram_identity is None


@pytest.mark.parametrize(
    "token",
    ["A" * 43, "short", "A" * 44, "A" * 5000, "../../etc/passwd", "%00" * 10, "A" * 42 + "!"],
)
def test_forged_or_malformed_tokens_are_rejected(client, user, token):
    web_login(client)
    response = client.get(f"/auth/telegram/link/{token}")
    assert response.status_code in (400, 404)
    assert TelegramIdentity.query.count() == 0


def test_link_tokens_cannot_be_brute_forced(client):
    statuses = [client.get(f"/auth/telegram/link/{'B' * 42}{i % 10}").status_code for i in range(31)]
    assert statuses[-1] == 429


def test_only_the_newest_link_of_a_telegram_user_works(client, user, mail):
    web_login(client)
    old_path, _ = request_link(client)
    new_path, _ = request_link(client)

    assert client.get(old_path).status_code == 400
    assert client.get(new_path).status_code == 302


def test_cross_site_confirmation_is_blocked(client, user, mail):
    """CSRF: an attacker page auto-submits the victim's pending confirmation."""
    web_login(client)
    path, _ = request_link(client, tg_id=TG_MALLORY, username="mallory")
    client.get(path)
    csrf = pending_csrf(client)

    cross_site = client.post(
        "/auth/telegram/link/confirm",
        data={"csrf_token": csrf},
        headers={"Origin": "https://evil.example"},
    )
    no_token = client.post("/auth/telegram/link/confirm", data={})
    wrong_token = client.post("/auth/telegram/link/confirm", data={"csrf_token": "x" * 43})

    assert cross_site.status_code == 403
    assert no_token.status_code == 400 and wrong_token.status_code == 400
    assert TelegramIdentity.query.count() == 0


def test_stolen_or_old_session_must_sign_in_again_to_link(client, user, mail):
    """Stolen cookie -> link own Telegram = access that survives a password
    change. Linking needs a sign-in from the last 15 minutes."""
    web_login(client)
    path, _ = request_link(client, tg_id=TG_MALLORY, username="mallory")
    client.get(path)
    csrf = pending_csrf(client)
    with client.session_transaction() as session:
        session["auth_at"] = int(time.time()) - 16 * 60

    page = client.get("/auth/telegram/link")
    confirm = client.post("/auth/telegram/link/confirm", data={"csrf_token": csrf})

    assert page.status_code == 302 and page.location.endswith("/auth/login")
    assert confirm.status_code == 302 and confirm.location.endswith("/auth/login")
    assert TelegramIdentity.query.count() == 0

    # Signing in again brings the user back to the same confirmation.
    assert web_login(client).location.endswith("/auth/telegram/link")
    response = client.post("/auth/telegram/link/confirm", data={"csrf_token": pending_csrf(client)})
    assert response.status_code == 200 and TelegramIdentity.query.count() == 1


def test_remembered_session_without_sign_in_time_cannot_link(client, user, mail):
    path, _ = request_link(client)
    client.get(path)
    browser_session_for(client, user)  # like a "remember me" restore: no auth_at
    with client.session_transaction() as session:
        session.pop("auth_at", None)

    assert client.get("/auth/telegram/link").location.endswith("/auth/login")
    assert TelegramIdentity.query.count() == 0


def test_confirmation_requires_a_signed_in_user(client, user, mail):
    path, _ = request_link(client)
    client.get(path)
    csrf = pending_csrf(client)

    response = client.post("/auth/telegram/link/confirm", data={"csrf_token": csrf})

    assert response.status_code == 302 and "/auth/login" in response.location
    assert TelegramIdentity.query.count() == 0


def test_forged_fields_cannot_choose_the_telegram_account_or_user(client, user, mail):
    victim = make_user("victim@example.com")
    web_login(client)
    path, _ = request_link(client, tg_id=TG_ALICE)
    client.get(path)

    client.post(
        "/auth/telegram/link/confirm?telegram_user_id=%d&user_id=%d" % (TG_MALLORY, victim.id),
        data={
            "csrf_token": pending_csrf(client),
            "telegram_user_id": TG_MALLORY,
            "user_id": victim.id,
        },
    )

    identity = TelegramIdentity.query.one()
    assert (identity.user_id, identity.telegram_user_id) == (user.id, TG_ALICE)


def test_session_swap_pending_link_does_not_survive_logout(client, user, mail):
    """Shared computer: A opens the link and walks away; B logs in later."""
    path, _ = request_link(client)
    client.get(path)
    client.get("/auth/logout")

    make_user("b@example.com")
    response = web_login(client, "b@example.com")

    assert not response.location.endswith("/auth/telegram/link")
    with client.session_transaction() as session:
        assert "tg_link" not in session


def test_form_token_changes_on_login(client, user, mail):
    """A form token planted before login is useless after it."""
    path, _ = request_link(client)
    client.get(path)
    before = pending_csrf(client)

    web_login(client)

    assert pending_csrf(client) != before
    assert client.post("/auth/telegram/link/confirm", data={"csrf_token": before}).status_code == 400


def test_telegram_linked_to_someone_else_cannot_be_moved(client, user, victim_identity, mail):
    response = bot_post(client, "/api/telegram/link-token", tg_payload())
    assert response.status_code == 409 and response.json["code"] == "already_linked"


def test_telegram_linked_elsewhere_after_link_issued(app, user, mail):
    attacker_browser = app.test_client()
    web_login(attacker_browser)
    path, _ = request_link(attacker_browser)
    attacker_browser.get(path)

    owner = make_user("owner@example.com")
    link(owner, TG_ALICE)

    response = attacker_browser.post(
        "/auth/telegram/link/confirm", data={"csrf_token": pending_csrf(attacker_browser)}
    )

    assert response.status_code == 409
    assert TelegramIdentity.query.one().user_id == owner.id


def test_user_with_a_telegram_cannot_get_a_second_one(client, user, mail):
    link(user, TG_MALLORY)
    web_login(client)
    path, _ = request_link(client, tg_id=TG_ALICE)
    client.get(path)
    assert "csrf_token" not in client.get("/auth/telegram/link").get_data(as_text=True)

    response = client.post("/auth/telegram/link/confirm", data={"csrf_token": pending_csrf(client)})

    assert response.status_code == 409
    assert TelegramIdentity.query.filter_by(telegram_user_id=TG_ALICE).count() == 0


def test_link_works_only_in_the_first_browser_that_opens_it(app, user, mail):
    """A copy of the URL (logs, history, shoulder-surfing) is dead once opened."""
    other = make_user("other@example.com")
    a, b = app.test_client(), app.test_client()
    web_login(a)
    web_login(b, "other@example.com")
    path, token = request_link(a)

    assert a.get(path).status_code == 302
    assert b.get(path).status_code == 400
    assert TelegramLinkToken.query.filter_by(token_hash=tg.hash_link_token(token)).count() == 0

    first = a.post("/auth/telegram/link/confirm", data={"csrf_token": pending_csrf(a)})

    assert first.status_code == 200
    assert TelegramIdentity.query.one().user_id == user.id
    assert other.telegram_identity is None


def test_cloned_session_cannot_confirm_twice(app, user, mail):
    """Two browsers sharing one pending link (copied cookie): one wins."""
    other = make_user("other@example.com")
    a, b = app.test_client(), app.test_client()
    web_login(a)
    path, _ = request_link(a)
    a.get(path)
    with a.session_transaction() as session:
        pending = dict(session["tg_link"])
    web_login(b, "other@example.com")
    with b.session_transaction() as session:
        session["tg_link"] = pending

    first = a.post("/auth/telegram/link/confirm", data={"csrf_token": pending_csrf(a)})
    second = b.post("/auth/telegram/link/confirm", data={"csrf_token": pending_csrf(b)})

    assert first.status_code == 200 and second.status_code == 400
    assert TelegramIdentity.query.one().user_id == user.id
    assert other.telegram_identity is None


def test_concurrent_consumption_of_one_token(app, user, mail):
    """Threads hit the conditional UPDATE at the same time: one wins."""
    import threading

    token = None
    with app.test_request_context():
        token = tg.issue_link_token(TG_ALICE, username=None, name=None, ttl_seconds=600)
    token_hash = tg.hash_link_token(token)
    results = []
    barrier = threading.Barrier(4)

    def worker():
        with app.app_context():
            barrier.wait()
            row = tg.consume_link_token(token_hash)
            db.session.commit()
            results.append(row is not None)
            db.session.remove()

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(results) == [False, False, False, True]


def test_cancel_spends_the_link(client, user, mail):
    web_login(client)
    path, _ = request_link(client)
    client.get(path)

    client.post("/auth/telegram/link/cancel", data={"csrf_token": pending_csrf(client)})

    assert client.get(path).status_code == 400
    assert TelegramLinkToken.query.one().used_at is not None
    assert TelegramIdentity.query.count() == 0


def test_telegram_name_is_escaped_on_the_confirmation_page(client, user, mail):
    web_login(client)
    path, _ = request_link(client, username=None, name="<script>alert(1)</script>")
    client.get(path)

    page = client.get("/auth/telegram/link").get_data(as_text=True)

    assert "<script>alert(1)</script>" not in page


def test_pending_link_survives_github_login(client, user, mail, monkeypatch, app):
    from unittest.mock import MagicMock

    app.config["GITHUB_CLIENT_ID"], app.config["GITHUB_CLIENT_SECRET"] = "id", "secret"
    path, _ = request_link(client)
    client.get(path)

    token_response = MagicMock()
    token_response.json.return_value = {"access_token": "T"}
    user_response, email_response = MagicMock(), MagicMock()
    user_response.json.return_value = {"id": 1, "login": "x"}
    email_response.json.return_value = [{"email": "test@example.com", "primary": True, "verified": True}]
    monkeypatch.setattr("web.app.routes.auth.oauth_github.requests.post", lambda *a, **k: token_response)
    responses = iter([user_response, email_response])
    monkeypatch.setattr("web.app.routes.auth.oauth_github.requests.get", lambda *a, **k: next(responses))
    with client.session_transaction() as session:
        session["github_oauth_state"] = "STATE"

    response = client.get("/auth/github/callback?code=c&state=STATE")

    assert response.location.endswith("/auth/telegram/link")
    assert TelegramIdentity.query.count() == 0


def test_production_link_needs_public_base_url(client, app):
    app.config["PUBLIC_BASE_URL"] = None
    app.config["IS_PRODUCTION"] = True
    response = bot_post(client, "/api/telegram/link-token", tg_payload(), headers={"Host": "evil.example"})
    assert response.status_code == 503


def test_link_url_uses_canonical_base_not_host_header(client, app):
    app.config["PUBLIC_BASE_URL"] = "https://nosifit.example"
    response = bot_post(client, "/api/telegram/link-token", tg_payload(), headers={"Host": "evil.example"})
    assert response.json["url"].startswith("https://nosifit.example/auth/telegram/link/")


# --- Disconnecting -----------------------------------------------------------------------------


def test_disconnect_with_password(client, user, mail):
    link(user, TG_ALICE)
    bot = app_client(client)
    bot_post(bot, "/api/telegram/login", tg_payload())
    web_login(client)

    response = client.post("/profile/telegram/disconnect", json={"password": PASSWORD})

    assert response.status_code == 200 and response.json["status"] == "disconnected"
    assert TelegramIdentity.query.count() == 0
    assert bot.get("/api/nutrition/water").status_code == 401
    assert any("відключено" in m["subject"] for m in mail)


def test_stolen_session_cannot_disconnect_without_password(client, user, mail):
    link(user, TG_ALICE)
    web_login(client)

    statuses = [
        client.post("/profile/telegram/disconnect", json={"password": "guess"}).status_code
        for _ in range(11)
    ]

    assert statuses[:10] == [400] * 10 and statuses[10] == 429
    assert TelegramIdentity.query.count() == 1


def test_disconnect_with_email_code_for_accounts_without_password(client, mail):
    user = make_user("oauth@example.com", password=None)
    db.session.add(OAuthAccount(provider="google", provider_user_id="g1", user_id=user.id))
    db.session.commit()
    link(user, TG_ALICE)
    browser_session_for(client, user)

    assert client.post("/profile/telegram/disconnect", json={"code": "123456"}).json["message"] == "expired"
    assert client.post("/profile/telegram/disconnect/request").json["status"] == "sent"
    code = mail[-1]["code"]
    wrong = "000000" if code != "000000" else "111111"
    assert client.post("/profile/telegram/disconnect", json={"code": wrong}).status_code == 400

    response = client.post("/profile/telegram/disconnect", json={"code": code})

    assert response.status_code == 200
    assert TelegramIdentity.query.count() == 0


def test_last_sign_in_method_cannot_be_disconnected(client, mail):
    user = make_user("tgonly@example.com", password=None)
    link(user, TG_ALICE)
    browser_session_for(client, user)

    response = client.post("/profile/telegram/disconnect", json={"code": "123456"})

    assert response.status_code == 400 and response.json["message"] == "last_method"
    assert TelegramIdentity.query.count() == 1


def test_disconnect_requires_login_and_same_origin(client, user):
    link(user, TG_ALICE)
    assert client.post("/profile/telegram/disconnect", json={"password": PASSWORD}).status_code in (302, 401)

    web_login(client)
    response = client.post(
        "/profile/telegram/disconnect",
        json={"password": PASSWORD},
        headers={"Origin": "https://evil.example"},
    )
    assert response.status_code == 403
    assert TelegramIdentity.query.count() == 1


def test_disconnect_cannot_target_another_user(client, user, victim_identity):
    """IDOR: ids in the request are ignored; only the caller's link is touched."""
    web_login(client)

    response = client.post(
        "/profile/telegram/disconnect",
        json={
            "password": PASSWORD,
            "user_id": victim_identity.user_id,
            "telegram_user_id": TG_ALICE,
        },
    )

    assert response.status_code == 404
    assert TelegramIdentity.query.count() == 1


def test_disconnect_sequence_keeps_one_method(client, mail):
    """GitHub + Telegram, no password: removing one leaves the other locked in."""
    user = make_user("two@example.com", password=None)
    db.session.add(OAuthAccount(provider="github", provider_user_id="1", user_id=user.id))
    db.session.commit()
    link(user, TG_ALICE)
    browser_session_for(client, user)

    assert client.post("/profile/oauth_disconnect", data={"provider": "github"}).status_code == 200
    client.post("/profile/telegram/disconnect/request")
    response = client.post("/profile/telegram/disconnect", json={"code": mail[-1]["code"]})

    assert response.json["message"] == "last_method"
    assert TelegramIdentity.query.count() == 1


def test_concurrent_disconnects_cannot_remove_every_method(app, mail):
    """Two workers remove GitHub and Telegram at once; one must refuse."""
    import threading

    user = make_user("race2@example.com", password=None)
    db.session.add(OAuthAccount(provider="github", provider_user_id="1", user_id=user.id))
    db.session.commit()
    link(user, TG_ALICE)
    user_id = user.id
    results = []
    barrier = threading.Barrier(2)

    def remove(method):
        with app.app_context():
            locked_user = db.session.get(User, user_id)
            barrier.wait()
            if method == "telegram":
                results.append(tg.unlink_telegram(locked_user))
            else:
                locked = tg.lock_user(user_id)
                if tg.remaining_methods_without(locked, "github") == 0:
                    db.session.rollback()
                    results.append("last_method")
                else:
                    OAuthAccount.query.filter_by(user_id=user_id).delete()
                    db.session.commit()
                    results.append("unlinked")
            db.session.remove()

    threads = [threading.Thread(target=remove, args=(m,)) for m in ("telegram", "github")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    db.session.expire_all()
    remaining = OAuthAccount.query.count() + TelegramIdentity.query.count()
    assert sorted(results) == ["last_method", "unlinked"]
    assert remaining == 1


def test_oauth_disconnect_refuses_last_method(client):
    user = make_user("gh@example.com", password=None)
    db.session.add(OAuthAccount(provider="github", provider_user_id="1", user_id=user.id))
    db.session.commit()
    browser_session_for(client, user)

    response = client.post("/profile/oauth_disconnect", data={"provider": "github"})

    assert response.status_code == 400 and response.json["error"] == "last_method"
    assert OAuthAccount.query.count() == 1


# --- Account deletion, profile page, model constraints -----------------------------------


def test_account_deletion_frees_the_telegram_account(client, mail):
    register(client, mail)
    user = User.query.filter_by(email="new@example.com").one()
    delete_user_account(user)

    response = register(app_client(client), mail, email="again@example.com")

    assert response.status_code == 201
    assert TelegramIdentity.query.one().user.email == "again@example.com"


def test_profile_shows_connected_accounts(client, user, app):
    app.config["TELEGRAM_BOT_USERNAME"] = "NosiFitBot"
    web_login(client)
    page = client.get("/profile/").get_data(as_text=True)
    assert "https://t.me/NosiFitBot?start=connect" in page

    link(user, TG_ALICE, "alice_tg")
    page = client.get("/profile/").get_data(as_text=True)
    assert "@alice_tg" in page and "modal-telegram-disconnect" in page


def test_one_telegram_one_user_in_the_database(app, user):
    from sqlalchemy.exc import IntegrityError

    other = make_user("o@example.com")
    link(user, TG_ALICE)

    db.session.add(TelegramIdentity(user_id=other.id, telegram_user_id=TG_ALICE))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()

    db.session.add(TelegramIdentity(user_id=user.id, telegram_user_id=TG_MALLORY))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_no_secrets_in_logs(client, mail, caplog):
    import logging

    caplog.set_level(logging.DEBUG)
    register(client, mail, email="logs@example.com")
    path, token = request_link(app_client(client), tg_id=TG_MALLORY)

    code = mail[0]["text"]
    digits = re.search(r"\b(\d{6})\b", code).group(1)
    logged = caplog.text
    assert digits not in logged and token not in logged and SECRET not in logged
    assert "logs@example.com" not in logged
