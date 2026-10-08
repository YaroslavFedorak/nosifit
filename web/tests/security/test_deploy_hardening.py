"""Things that must hold before the site is public."""

import importlib

from backend.app.extensions import db
from backend.app.models.recovery.habit import RecoveryHabit
from backend.app.models.recovery.user_habit import UserRecoveryHabit
from backend.app.models.user import User
from werkzeug.security import generate_password_hash


def login(client, email="test@example.com", password="password123"):
    return client.post("/auth/login", data={"email": email, "password": password})


def make_other_user_with_habit():
    other = User(username="other", email="other@example.com", password=generate_password_hash("x" * 12))
    habit = RecoveryHabit(slug="walk", name="Walk", points=1)
    db.session.add_all([other, habit])
    db.session.flush()
    user_habit = UserRecoveryHabit(user_id=other.id, habit_id=habit.id, is_active=True)
    db.session.add(user_habit)
    db.session.commit()
    return other.id, user_habit.id


def test_recovery_api_requires_login(client):
    assert client.get("/api/recovery/habits/list").status_code == 401
    assert client.get("/api/recovery/snapshot/1").status_code == 401
    assert client.post("/api/recovery/sleep", json={}).status_code == 401


def test_recovery_api_hides_other_users_data(app, client, user):
    with app.app_context():
        other_id, other_habit_id = make_other_user_with_habit()

    login(client)

    for path in (
        f"/api/recovery/snapshot/{other_id}",
        f"/api/recovery/heatmap/{other_id}",
        f"/api/recovery/habits/user/{other_id}",
        f"/api/recovery/recommendations/{other_id}",
        f"/api/recovery/day-details/{other_id}",
    ):
        assert client.get(path).status_code == 404, path

    assert client.delete(f"/api/recovery/habits/{other_habit_id}").status_code == 404
    assert client.post("/api/recovery/habits/logs", json={"user_habit_id": other_habit_id}).status_code == 404
    assert client.delete(f"/api/recovery/habits/logs/{other_habit_id}").status_code == 404

    with app.app_context():
        assert db.session.get(UserRecoveryHabit, other_habit_id).is_active is True


def test_sleep_is_always_saved_for_current_user(app, client, user):
    with app.app_context():
        other_id, _ = make_other_user_with_habit()

    login(client)
    response = client.post(
        "/api/recovery/sleep",
        json={"user_id": other_id, "sleep_start": "2026-10-05T23:00:00", "sleep_end": "2026-10-06T07:00:00"},
    )
    assert response.status_code == 201

    with app.app_context():
        from backend.app.models.recovery.sleep_entry import SleepEntry

        assert SleepEntry.query.filter_by(user_id=other_id).count() == 0
        assert SleepEntry.query.filter_by(user_id=user.id).count() == 1


def test_premium_self_activation_can_be_disabled(app, client, user):
    app.config["PREMIUM_SELF_ACTIVATION"] = False
    login(client)
    assert client.get("/premium/activate").status_code == 404


def test_database_url_is_normalized_for_psycopg3(monkeypatch):
    import backend.config as config

    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@host:5432/db")
    assert importlib.reload(config).Config.SQLALCHEMY_DATABASE_URI == "postgresql+psycopg://u:p@host:5432/db"

    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@host/db")
    assert importlib.reload(config).Config.SQLALCHEMY_DATABASE_URI == "postgresql+psycopg://u:p@host/db"


def test_sendgrid_is_used_when_api_key_is_set(app, monkeypatch):
    from backend.app.utils import mailer

    calls = []

    class Response:
        status_code = 200
        text = "{}"

    def fake_post(url, json, headers, timeout):
        calls.append((url, json, headers))
        return Response()

    monkeypatch.setattr(mailer.requests, "post", fake_post)
    app.config["SENDGRID_API_KEY"] = "SG.test"
    app.config["MAIL_FROM"] = "NosiFit <no-reply@example.com>"

    with app.app_context():
        mailer.send_email("someone@example.com", "Hi", "Text")

    url, payload, headers = calls[0]
    assert url == "https://api.sendgrid.com/v3/mail/send"
    assert payload["personalizations"][0]["to"] == [{"email": "someone@example.com"}]
    assert payload["from"] == {"email": "no-reply@example.com", "name": "NosiFit"}
    assert headers["Authorization"] == "Bearer SG.test"


def test_brevo_is_used_when_api_key_is_set(app, monkeypatch):
    from backend.app.utils import mailer

    calls = []

    class Response:
        status_code = 201
        text = "{}"

    def fake_post(url, json, headers, timeout):
        calls.append((url, json, headers))
        return Response()

    monkeypatch.setattr(mailer.requests, "post", fake_post)
    app.config["BREVO_API_KEY"] = "xkeysib-test"
    app.config["SENDGRID_API_KEY"] = "SG.test"
    app.config["MAIL_FROM"] = "NosiFit <me@gmail.com>"

    with app.app_context():
        mailer.send_email("someone@example.com", "Hi", "Text", html="<b>Hi</b>")

    url, payload, headers = calls[0]
    assert url == "https://api.brevo.com/v3/smtp/email"
    assert payload["sender"] == {"email": "me@gmail.com", "name": "NosiFit"}
    assert payload["to"] == [{"email": "someone@example.com"}]
    assert payload["htmlContent"] == "<b>Hi</b>"
    assert headers["api-key"] == "xkeysib-test"


def test_sendgrid_without_sender_raises(app, monkeypatch):
    import pytest
    from backend.app.utils import mailer

    monkeypatch.setattr(mailer.requests, "post", lambda *a, **k: pytest.fail("must not call SendGrid"))
    app.config["SENDGRID_API_KEY"] = "SG.test"
    app.config["MAIL_FROM"] = None

    with app.app_context(), pytest.raises(mailer.EmailSendError):
        mailer.send_email("someone@example.com", "Hi", "Text")


def test_email_codes_are_not_stored_in_plain_text(app, client, user, monkeypatch):
    from backend.app.utils import mailer

    sent = {}
    monkeypatch.setattr(mailer, "send_email", lambda to, subject, text, html=None: sent.update(text=text))

    login(client)
    assert client.post("/profile/delete/request").status_code == 200

    code = sent["text"].rsplit(" ", 1)[-1]
    with client.session_transaction() as session:
        assert session["delete_code"] != code
        assert code not in str(dict(session))

    assert client.post("/profile/delete/confirm", json={"code": "000000"}).get_json()["status"] == "wrong"
    assert client.post("/profile/delete/confirm", json={"code": code}).get_json()["status"] == "ok"
