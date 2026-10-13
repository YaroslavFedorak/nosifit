"""The email outbox: queued in the request, sent in the background, retried,
never lost on restart, never sent twice by two workers, and logged without
addresses or text."""

import importlib.util
import logging
import threading
import time
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy.exc import OperationalError

from backend.app.extensions import db
from backend.app.models.email_outbox import EmailOutbox
from backend.app.services import email_outbox
from backend.app.utils.mailer import EmailSendError

ROOT = Path(__file__).resolve().parents[3]
ADDRESS = "someone@example.com"
TEXT = "Secret-ish body text"


@pytest.fixture
def provider(monkeypatch):
    """The email service: records what it accepted, can be made to fail."""

    class Provider:
        sent = []
        failing = False

        def __call__(self, to, subject, text, html=None):
            if self.failing:
                raise EmailSendError("Email service is unavailable")
            self.sent.append({"to": to, "subject": subject, "text": text})

    fake = Provider()
    fake.sent = []
    monkeypatch.setattr(email_outbox, "send_email", fake)
    return fake


def rows():
    db.session.expire_all()
    return EmailOutbox.query.order_by(EmailOutbox.id).all()


def make_due(row):
    row.next_attempt_at = email_outbox.utcnow() - timedelta(seconds=1)
    db.session.commit()


def test_queued_in_the_request_sent_by_the_worker(app, provider):
    email_outbox.enqueue("test", ADDRESS, "Hello", TEXT)

    assert provider.sent == []
    (row,) = rows()
    assert (row.status, row.attempts) == ("pending", 0)

    assert email_outbox.process_due() == {"sent": 1}
    assert provider.sent == [{"to": ADDRESS, "subject": "Hello", "text": TEXT}]
    (row,) = rows()
    assert row.status == "sent" and row.sent_at is not None and row.locked_until is None


def test_a_failure_is_retried_later_then_sent(app, provider):
    email_outbox.enqueue("test", ADDRESS, "Hello", TEXT)
    provider.failing = True

    assert email_outbox.process_due() == {"pending": 1}
    (row,) = rows()
    assert row.attempts == 1 and row.last_error == "Email service is unavailable"
    wait = row.next_attempt_at - email_outbox.utcnow()
    assert timedelta(seconds=20) < wait <= timedelta(seconds=30)

    # Not due yet: nothing happens.
    provider.failing = False
    assert email_outbox.process_due() == {}

    make_due(row)
    assert email_outbox.process_due() == {"sent": 1}
    assert rows()[0].attempts == 2
    assert len(provider.sent) == 1


def test_it_gives_up_after_max_attempts_and_logs_without_personal_data(app, provider, caplog, monkeypatch):
    # The test session's Alembic run (logging.config.fileConfig) disables
    # loggers created before it; production runs migrations in another process.
    monkeypatch.setattr(email_outbox.logger, "disabled", False)
    email_outbox.enqueue("test", ADDRESS, "Hello", TEXT)
    provider.failing = True

    with caplog.at_level(logging.WARNING, logger=email_outbox.__name__):
        for _ in range(email_outbox.MAX_ATTEMPTS):
            make_due(rows()[0])
            email_outbox.process_due()

    (row,) = rows()
    assert row.status == "failed" and row.attempts == email_outbox.MAX_ATTEMPTS
    assert email_outbox.process_due() == {}
    assert [r.levelname for r in caplog.records].count("ERROR") == 1
    logged = caplog.text
    assert ADDRESS not in logged and TEXT not in logged
    assert email_outbox.counts()["failed"] == 1


def test_retry_delays_grow():
    delays = [email_outbox.retry_delay(n) for n in range(1, email_outbox.MAX_ATTEMPTS)]

    assert delays == sorted(delays) and delays[0] == timedelta(seconds=30)


def test_the_same_key_is_queued_once(app, provider):
    email_outbox.enqueue("test", ADDRESS, "Hello", TEXT, dedup_key="once")
    email_outbox.enqueue("test", ADDRESS, "Hello", TEXT, dedup_key="once")

    assert len(rows()) == 1
    email_outbox.process_due()
    email_outbox.process_due()
    assert len(provider.sent) == 1


def test_a_row_taken_by_another_worker_is_left_alone(app, provider):
    email_outbox.enqueue("test", ADDRESS, "Hello", TEXT)
    (row,) = rows()
    row.status, row.locked_until = "sending", email_outbox.utcnow() + timedelta(minutes=5)
    db.session.commit()

    assert email_outbox.process_due() == {}
    assert provider.sent == []


def test_a_row_left_by_a_dead_worker_is_sent_after_its_lease(app, provider):
    email_outbox.enqueue("test", ADDRESS, "Hello", TEXT)
    (row,) = rows()
    row.status, row.attempts = "sending", 1
    row.locked_until = email_outbox.utcnow() - timedelta(seconds=1)
    db.session.commit()

    assert email_outbox.process_due() == {"sent": 1}
    assert rows()[0].attempts == 2


def test_stopping_gives_untried_rows_back(app, provider):
    for n in range(3):
        email_outbox.enqueue("test", f"{n}@example.com", "Hello", TEXT)
    stopping = threading.Event()
    stopping.set()

    assert email_outbox.process_due(stopping=stopping) == {}
    assert [(r.status, r.attempts, r.locked_until) for r in rows()] == [("pending", 0, None)] * 3
    assert provider.sent == []


def test_old_done_rows_are_purged(app, provider):
    for kind in ("old_sent", "old_failed", "new_sent", "pending"):
        email_outbox.enqueue(kind, ADDRESS, "Hello", TEXT)
    now = email_outbox.utcnow()
    for row in rows():
        if row.kind.startswith("old"):
            row.created_at = now - timedelta(days=40)
        row.status = {"old_sent": "sent", "old_failed": "failed", "new_sent": "sent"}.get(row.kind, "pending")
    db.session.commit()

    assert email_outbox.purge_done() == 2
    assert sorted(r.kind for r in rows()) == ["new_sent", "pending"]


def test_a_database_error_never_fails_the_operation(app, monkeypatch, caplog):
    def broken(*args, **kwargs):
        raise OperationalError("INSERT INTO email_outbox", {"to_address": ADDRESS, "body_text": TEXT},
                               Exception("connection lost"))

    monkeypatch.setattr(db.session, "execute", broken)
    monkeypatch.setattr(email_outbox.logger, "disabled", False)

    with caplog.at_level(logging.WARNING, logger=email_outbox.__name__):
        assert email_outbox.enqueue_notice("test", ADDRESS, "Hello", TEXT) is False

    assert "Could not queue the test notice: OperationalError" in caplog.text
    assert ADDRESS not in caplog.text and TEXT not in caplog.text


def test_the_worker_thread_sends_and_stops_cleanly(app, provider):
    worker = email_outbox.start_worker(app, poll_seconds=0.05)
    try:
        email_outbox.enqueue("test", ADDRESS, "Hello", TEXT)
        deadline = time.monotonic() + 5
        while not provider.sent and time.monotonic() < deadline:
            time.sleep(0.02)
        assert len(provider.sent) == 1
    finally:
        assert email_outbox.stop_worker(timeout=5) is True
    assert worker._thread.is_alive() is False
    assert rows()[0].status == "sent"


def test_gunicorn_hooks_start_and_stop_the_worker(app, provider):
    spec = importlib.util.spec_from_file_location("gunicorn_conf", ROOT / "gunicorn.conf.py")
    conf = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(conf)

    class FakeWorker:
        wsgi = app

    conf.post_worker_init(FakeWorker())
    try:
        assert email_outbox._worker is not None and email_outbox._worker._thread.is_alive()
    finally:
        conf.worker_exit(None, FakeWorker())
    assert email_outbox._worker is None


# --- The notices that use it --------------------------------------------------------------


def test_security_notices_are_queued_not_sent_in_the_request(app, provider, user):
    from backend.app.services import telegram_auth as tg

    tg.notify_telegram_linked(user, "alice_tg")
    tg.notify_telegram_unlinked(user)

    assert provider.sent == []
    assert [(r.kind, r.to_address) for r in rows()] == [
        ("telegram_linked", user.email),
        ("telegram_unlinked", user.email),
    ]
    assert email_outbox.process_due() == {"sent": 2}
    assert "@alice_tg" in provider.sent[0]["text"]


def test_outside_gunicorn_the_first_email_starts_the_worker(app, provider, monkeypatch):
    """The development server reads no gunicorn.conf.py."""
    monkeypatch.setitem(app.config, "TESTING", False)
    assert email_outbox._worker is None
    try:
        email_outbox.enqueue("test", ADDRESS, "Hello", TEXT)
        assert email_outbox._worker is not None
        deadline = time.monotonic() + 5
        while not provider.sent and time.monotonic() < deadline:
            time.sleep(0.02)
        assert len(provider.sent) == 1
    finally:
        assert email_outbox.stop_worker(timeout=5) is True
