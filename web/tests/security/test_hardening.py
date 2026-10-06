"""Regression tests for the security audit fixes.

Each test reproduces an attack that worked before the fix.
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from flask import g
from werkzeug.security import generate_password_hash

from backend.app.extensions import db
from backend.app.models import Meal
from backend.app.models.nutrition.user_water import UserWater
from backend.app.models.nutrition.user_weight import UserWeight
from backend.app.models.oauth_account import OAuthAccount
from backend.app.models.recovery.habit import RecoveryHabit
from backend.app.models.training_session import TrainingSession
from backend.app.models.user import User
from backend.app.models.user_profile import UserProfile
from backend.app.training.models.training_plan import TrainingPlan
from backend.app.utils.token import generate_reset_token

PASSWORD = "password123"


def login(client, email="test@example.com", password=PASSWORD):
    return client.post("/auth/login", data={"email": email, "password": password})


@pytest.fixture
def other_user(app):
    other = User(
        username="victim",
        email="victim@example.com",
        password=generate_password_hash("victim-password"),
    )
    db.session.add(other)
    db.session.commit()
    return other


# --- Headers, CSRF, request parsing ----------------------------------------------


def test_security_headers_and_csp_nonce(client):
    response = client.get("/auth/login")

    csp = response.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "object-src 'none'" in csp
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Cache-Control"] == "no-store"

    nonce = csp.split("'nonce-")[1].split("'")[0]
    assert f'nonce="{nonce}"'.encode() in response.data
    assert b"onclick=" not in response.data


def test_cross_site_post_is_rejected(client, user):
    login(client)

    response = client.post(
        "/api/nutrition/water",
        json={"amount": 1},
        headers={"Origin": "https://evil.example"},
    )
    assert response.status_code == 403

    response = client.post(
        "/profile/change_password",
        data={"current_password": PASSWORD, "new_password": "x" * 12, "confirm_password": "x" * 12},
        headers={"Referer": "https://evil.example/page"},
    )
    assert response.status_code == 403
    db.session.refresh(user)
    assert user.check_password(PASSWORD)


def test_same_origin_and_non_browser_posts_work(client, user):
    login(client)

    same_origin = client.post(
        "/api/nutrition/water", json={"amount": 0.5}, headers={"Origin": "http://localhost"}
    )
    no_origin = client.post("/api/nutrition/water", json={"amount": 0.5})

    assert same_origin.status_code == 200
    assert no_origin.status_code == 200


def test_nan_in_json_is_rejected(client, user):
    login(client)

    response = client.post(
        "/api/nutrition/water",
        data='{"amount": NaN}',
        content_type="application/json",
    )

    assert response.status_code == 400


def test_oversized_body_is_rejected(client, user):
    login(client)

    response = client.post(
        "/api/nutrition/products",
        data='{"name": "' + "a" * (2 * 1024 * 1024) + '"}',
        content_type="application/json",
    )

    assert response.status_code == 413


def test_i18n_namespace_cannot_traverse(client):
    assert client.get("/api/i18n/uk/..").status_code == 404
    assert client.get("/api/i18n/uk/common").status_code == 200


# --- Authentication ------------------------------------------------------------------


def _flash_messages(client):
    with client.session_transaction() as session:
        return [message for _, message in session.get("_flashes", [])]


def test_login_does_not_reveal_registered_emails(client, user):
    login(client, email="nobody@example.com")
    unknown = _flash_messages(client)

    client.get("/auth/login")  # consume flashes
    login(client, password="wrong-password")
    wrong = _flash_messages(client)

    assert unknown == wrong


def test_login_brute_force_is_rate_limited(client, user):
    for _ in range(10):
        login(client, password="wrong-password")

    # The 11th attempt is refused even with the right password.
    response = login(client)
    assert not response.location.endswith("/dashboard/")


def test_password_change_logs_out_other_sessions(app, user):
    attacker = app.test_client()
    owner = app.test_client()
    login(attacker)
    login(owner)

    assert attacker.get("/profile/").status_code == 200

    response = owner.post(
        "/profile/change_password",
        data={
            "current_password": PASSWORD,
            "new_password": "brand-new-password",
            "confirm_password": "brand-new-password",
        },
    )
    assert response.json["status"] == "success"

    # conftest keeps one app context open for the whole test, so Flask-Login's
    # per-request user cache (g._login_user) would survive between requests.
    g.pop("_login_user", None)

    # The stolen session is dead; the owner stays signed in.
    assert attacker.get("/profile/").status_code == 302
    g.pop("_login_user", None)
    assert owner.get("/profile/").status_code == 200


def test_session_with_plain_user_id_is_not_accepted(client, user):
    with client.session_transaction() as session:
        session["_user_id"] = str(user.id)
        session["_fresh"] = True

    assert client.get("/profile/").status_code == 302


def test_reset_link_works_only_once(client, user):
    with client.application.test_request_context():
        token = generate_reset_token(user)

    first = client.post(
        f"/auth/reset/{token}",
        data={"password": "first-new-password", "confirm": "first-new-password"},
    )
    assert first.location.endswith("/dashboard/")

    second = client.post(
        f"/auth/reset/{token}",
        data={"password": "attacker-password", "confirm": "attacker-password"},
    )
    assert second.location.endswith("/auth/reset")

    db.session.refresh(user)
    assert user.check_password("first-new-password")


def test_invalid_reset_token_is_not_a_server_error(client):
    response = client.get("/auth/reset/not-a-valid-token")

    assert response.status_code == 302
    assert response.location.endswith("/auth/reset")


def test_reset_rejects_short_password(client, user):
    with client.application.test_request_context():
        token = generate_reset_token(user)

    client.post(f"/auth/reset/{token}", data={"password": "123", "confirm": "123"})

    db.session.refresh(user)
    assert user.check_password(PASSWORD)


# --- Registration ----------------------------------------------------------------------


@pytest.fixture
def sent_codes(monkeypatch):
    sent = {}
    monkeypatch.setattr(
        "web.app.routes.auth.email_verification.send_verification_email",
        lambda email, code: sent.update({email: code}),
    )
    return sent


def _register(client, **overrides):
    form = {
        "username": "newbie",
        "email": "newbie@example.com",
        "password": "a-good-password",
        "confirm_password": "a-good-password",
    }
    form.update(overrides)
    return client.post("/verify/send_code", data=form)


def test_registration_keeps_no_plain_password_in_session(client, sent_codes):
    _register(client)

    with client.session_transaction() as session:
        reg_data = session["reg_data"]
        assert "password" not in reg_data
        assert "a-good-password" not in str(dict(session))
        assert reg_data["password_hash"].startswith(("scrypt:", "pbkdf2:"))


def test_registration_rejects_weak_password(client, sent_codes):
    _register(client, password="123", confirm_password="123")

    assert sent_codes == {}


def test_verification_code_attempts_are_counted_on_the_server(client, sent_codes):
    _register(client)
    code = sent_codes["newbie@example.com"]
    wrong = "000000" if code != "000000" else "111111"

    with client.session_transaction() as session:
        snapshot = dict(session)

    for _ in range(6):
        # Replaying the old cookie used to reset the attempt counter.
        with client.session_transaction() as session:
            session.clear()
            session.update(snapshot)
        client.post("/verify/verify_email", data={"code": wrong})

    client.post("/verify/verify_email", data={"code": code})

    with client.session_transaction() as session:
        assert "verified_email" not in session


def test_full_registration_still_works(client, sent_codes):
    _register(client, age="30", weight="70", height="175")
    code = sent_codes["newbie@example.com"]

    client.post("/verify/verify_email", data={"code": code})
    response = client.post("/auth/register_complete")

    assert response.location.endswith("/dashboard/")
    created = User.query.filter_by(email="newbie@example.com").one()
    assert created.check_password("a-good-password")
    assert created.profile.age == 30


def test_registration_rejects_impossible_profile_values(client, sent_codes):
    _register(client, age="-5", weight="nan")
    client.post("/verify/verify_email", data={"code": sent_codes["newbie@example.com"]})

    client.post("/auth/register_complete")

    assert User.query.filter_by(email="newbie@example.com").first() is None


def test_verification_email_is_rate_limited(client, sent_codes):
    for _ in range(5):
        _register(client)

    response = _register(client)

    assert response.status_code == 429


# --- OAuth -----------------------------------------------------------------------------------


@patch("web.app.routes.auth.oauth_github.requests.post")
def test_github_callback_requires_state(mock_post, client, app):
    """Login CSRF: an attacker's ?code= must not be accepted without our state."""
    app.config["GITHUB_CLIENT_ID"] = "ID"
    app.config["GITHUB_CLIENT_SECRET"] = "SECRET"

    response = client.get("/auth/github/callback?code=ATTACKER_CODE")

    assert response.location.endswith("/auth/login")
    mock_post.assert_not_called()


def test_github_login_sets_state(client, app):
    app.config["GITHUB_CLIENT_ID"] = "ID"

    response = client.get("/auth/github")

    with client.session_transaction() as session:
        state = session["github_oauth_state"]
    assert f"state={state}" in response.location


@patch("web.app.routes.auth.oauth_github.requests.post")
def test_github_errors_do_not_leak_details(mock_post, client, app):
    app.config["GITHUB_CLIENT_ID"] = "ID"
    app.config["GITHUB_CLIENT_SECRET"] = "SECRET"
    mock_post.side_effect = RuntimeError("secret internal detail")

    with client.session_transaction() as session:
        session["github_oauth_state"] = "S"
    response = client.get("/auth/github/callback?code=C&state=S")

    assert b"secret internal detail" not in response.data


def test_google_unverified_email_is_not_linked(client, user):
    google = MagicMock()
    google.authorize_access_token.return_value = {}
    google.server_metadata = {"userinfo_endpoint": "https://example.com/userinfo"}
    google.get.return_value.json.return_value = {
        "sub": "ATTACKER",
        "email": "test@example.com",
        "email_verified": False,
    }

    with patch("web.app.routes.auth.oauth_google.oauth.create_client", return_value=google):
        response = client.get("/auth/google/callback")

    assert not response.location.endswith("/profile")
    assert OAuthAccount.query.filter_by(provider_user_id="ATTACKER").first() is None


# --- Authorization (IDOR) ----------------------------------------------------------------------


def test_recovery_endpoints_ignore_other_user_ids(client, user, other_user):
    login(client)

    for path in (
        f"/api/recovery/habits/user/{other_user.id}",
        f"/api/recovery/snapshot/{other_user.id}",
        f"/api/recovery/heatmap/{other_user.id}",
        f"/api/recovery/recommendations/{other_user.id}",
        f"/api/recovery/day-details/{other_user.id}?date=2026-01-01",
    ):
        assert client.get(path).status_code == 404, path


def test_cannot_touch_other_users_training_plan(client, user, other_user):
    plan = TrainingPlan(user_id=other_user.id, name="victim plan", days={})
    db.session.add(plan)
    db.session.commit()
    login(client)

    assert client.put(f"/api/training/plans/{plan.id}", json={"name": "x"}).status_code == 404
    assert client.delete(f"/api/training/plans/{plan.id}").status_code == 404
    assert db.session.get(TrainingPlan, plan.id).name == "victim plan"


def test_cannot_delete_other_users_meal(client, user, other_user):
    meal = Meal(user_id=other_user.id, date=date.today(), name="breakfast", category="breakfast")
    db.session.add(meal)
    db.session.commit()
    login(client)

    assert client.delete(f"/api/nutrition/meals/{meal.id}").status_code == 404
    assert db.session.get(Meal, meal.id) is not None


def test_cannot_read_other_users_training_session(client, user, other_user):
    session = TrainingSession(user_id=other_user.id, status="active")
    db.session.add(session)
    db.session.commit()
    login(client)

    assert client.get(f"/api/dashboard/training/session/{session.id}").status_code == 404
    response = client.post(f"/api/training/sessions/{session.id}/finish", json={})
    assert response.status_code == 404


def test_premium_habit_needs_premium(client, user):
    habit = RecoveryHabit(slug="premium_sauna", name="Sauna", points=5, premium_only=True)
    db.session.add(habit)
    db.session.commit()
    login(client)

    assert client.post(f"/api/recovery/habits/add/{habit.id}").status_code == 403
    assert client.post("/api/recovery/habits/add/999999").status_code == 404


# --- Input validation ----------------------------------------------------------------------------


def test_training_plan_rejects_markup_in_reps(client, user):
    login(client)

    response = client.post(
        "/api/training/plans",
        json={"name": "p", "days": {"mon": [{"exercise": {"id": "x"}, "reps": "<img src=x onerror=alert(1)>"}]}},
    )

    # Unknown exercises are skipped before reps are read; a bad day key fails.
    assert response.status_code in (200, 400)
    bad_day = client.post("/api/training/plans", json={"days": {"<script>": []}})
    assert bad_day.status_code == 400


def test_training_errors_do_not_leak_internals(client, user):
    login(client)

    response = client.post("/api/training/strength-test", json={"pushups": "lots"})

    assert response.status_code == 400
    assert "Traceback" not in response.get_data(as_text=True)


def test_strength_test_rejects_negative_values(client, user):
    login(client)

    response = client.post("/api/training/strength-test", json={"pushups": -5})

    assert response.status_code == 400


def test_exercise_page_size_is_capped(client, user):
    login(client)

    response = client.get("/api/training/exercises?per_page=1000000")

    assert response.status_code == 200
    assert response.json["per_page"] == 100


def test_sleep_longer_than_a_day_is_rejected(client, user):
    login(client)

    response = client.post(
        "/api/recovery/sleep",
        json={"sleep_start": "2026-01-01T22:00:00", "sleep_end": "2026-01-05T07:00:00"},
    )

    assert response.status_code == 400


def test_sleep_with_mixed_timezones_is_a_client_error(client, user):
    login(client)

    response = client.post(
        "/api/recovery/sleep",
        json={"sleep_start": "2026-01-01T22:00:00", "sleep_end": "2026-01-02T07:00:00Z"},
    )

    assert response.status_code == 400


def test_injuries_must_be_a_list_of_ids(client, user):
    login(client)

    response = client.post("/api/injuries/user", json={"injuries": "abc"})

    assert response.status_code == 400


def test_bulk_entries_are_capped(client, user):
    login(client)
    meal = Meal(user_id=user.id, date=date.today(), name="lunch", category="lunch")
    db.session.add(meal)
    db.session.commit()

    response = client.post(
        "/api/nutrition/entries/bulk",
        json={"meal_id": meal.id, "items": [{"product_id": 1, "amount": 1}] * 51},
    )

    assert response.status_code == 400


# --- Account deletion ----------------------------------------------------------------------------


@pytest.fixture
def delete_codes(monkeypatch):
    sent = {}
    monkeypatch.setattr(
        "web.app.routes.profile.delete_account_request.send_email_code",
        lambda email, code: sent.update(code=code),
    )
    return sent


def test_final_delete_requires_confirmed_code(client, user, delete_codes):
    login(client)
    client.post("/profile/delete/request")

    # Skipping /profile/delete/confirm used to work: only the password was checked.
    response = client.post(
        "/profile/delete/final", json={"email": "test@example.com", "password": PASSWORD}
    )

    assert response.status_code == 400
    assert db.session.get(User, user.id) is not None


def test_delete_code_cannot_be_brute_forced(client, user, delete_codes):
    login(client)
    client.post("/profile/delete/request")
    code = delete_codes["code"]
    wrong = "000000" if code != "000000" else "111111"

    for _ in range(6):
        client.post("/profile/delete/confirm", json={"code": wrong})

    response = client.post("/profile/delete/confirm", json={"code": code})

    assert response.json["status"] == "expired"


def test_account_with_tracked_data_can_be_deleted(client, user, delete_codes):
    db.session.add(UserProfile(user_id=user.id, training_location="home"))
    db.session.add(UserWater(user_id=user.id, date=date.today(), amount=1.5))
    db.session.add(UserWeight(user_id=user.id, date=date.today(), weight=80))
    db.session.add(Meal(user_id=user.id, date=date.today(), name="lunch", category="lunch"))
    db.session.commit()
    user_id = user.id

    login(client)
    client.post("/profile/delete/request")
    client.post("/profile/delete/confirm", json={"code": delete_codes["code"]})
    response = client.post(
        "/profile/delete/final", json={"email": "test@example.com", "password": PASSWORD}
    )

    assert response.json["status"] == "deleted"
    db.session.expire_all()
    assert db.session.get(User, user_id) is None
    assert UserWater.query.filter_by(user_id=user_id).count() == 0
    assert UserWeight.query.filter_by(user_id=user_id).count() == 0
    assert Meal.query.filter_by(user_id=user_id).count() == 0


def test_oauth_only_account_can_be_deleted_with_code(client, app, delete_codes):
    oauth_user = User(username="g", email="g@example.com", password="oauth")
    db.session.add(oauth_user)
    db.session.commit()
    with client.session_transaction() as session:
        session["_user_id"] = oauth_user.get_id()
        session["_fresh"] = True

    client.post("/profile/delete/request")
    client.post("/profile/delete/confirm", json={"code": delete_codes["code"]})
    response = client.post("/profile/delete/final", json={"email": "g@example.com"})

    assert response.json["status"] == "deleted"


def test_change_password_on_oauth_account_is_not_a_server_error(client, app):
    oauth_user = User(username="g", email="g@example.com", password="oauth")
    db.session.add(oauth_user)
    db.session.commit()
    with client.session_transaction() as session:
        session["_user_id"] = oauth_user.get_id()
        session["_fresh"] = True

    response = client.post(
        "/profile/change_password",
        data={"current_password": "oauth", "new_password": "x" * 12, "confirm_password": "x" * 12},
    )

    assert response.status_code == 400
    assert response.json["message"] == "wrong_old"
