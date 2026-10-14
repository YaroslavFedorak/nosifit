"""Emails sent in the background, durably: the email_outbox table.

``enqueue`` writes a row in the request's database; ``process_due`` sends
due rows. A worker thread in each web process (started by gunicorn.conf.py)
calls it when woken by ``enqueue`` and every POLL_SECONDS for retries.

Guarantees:
- a queued email survives restarts and deploys (it is a row in PostgreSQL);
- a failure is retried with a growing delay, MAX_ATTEMPTS times in all, then
  the row is marked failed and logged at ERROR (``python -m
  web.scripts.email_outbox`` lists them);
- the same ``dedup_key`` is queued once; two workers never take the same row
  (``FOR UPDATE SKIP LOCKED`` plus a lease);
- logs carry the row id and kind, never the address or the text.

Delivery is at least once: a worker that dies after the email service
accepted a message and before it recorded that, sends it again when the
lease runs out. Providers offer no idempotency key to close that gap.

Only notices whose failure the user never saw go through here (Telegram
connected/disconnected, email changed). Codes and links the user is waiting
for are still sent in the request, so a failure is still shown at once.
"""

import logging
import threading
import uuid
from datetime import datetime, timedelta, timezone

from flask import current_app
from sqlalchemy import delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

from backend.app.extensions import db
from backend.app.models.email_outbox import EmailOutbox
from backend.app.utils.mailer import EmailSendError, send_email

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 6
# Delay before attempt n+1 after n failures: 30 s, 2 min, 10 min, 30 min, 2 h.
RETRY_DELAYS = (
    timedelta(seconds=30),
    timedelta(minutes=2),
    timedelta(minutes=10),
    timedelta(minutes=30),
    timedelta(hours=2),
)
LEASE = timedelta(minutes=5)
BATCH_SIZE = 20
POLL_SECONDS = 30.0
KEEP_SENT = timedelta(days=7)
KEEP_FAILED = timedelta(days=30)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def retry_delay(failures: int) -> timedelta:
    return RETRY_DELAYS[min(failures, len(RETRY_DELAYS)) - 1]


def enqueue_notice(kind: str, to: str, subject: str, text: str) -> bool:
    """Queue a best-effort notice: a database error is logged, not raised,
    so it never fails the operation that was already done."""
    try:
        enqueue(kind, to, subject, text)
    except SQLAlchemyError as exc:
        db.session.rollback()
        # Not the exception text: SQLAlchemy puts the statement's parameters
        # (the address, the body) in it.
        logger.warning("Could not queue the %s notice: %s", kind, type(exc).__name__)
        return False
    return True


def enqueue(kind: str, to: str, subject: str, text: str, dedup_key: str | None = None) -> None:
    """Queue one email and commit. Raises on database errors, like any write."""
    statement = (
        insert(EmailOutbox)
        .values(
            dedup_key=dedup_key or f"{kind}:{uuid.uuid4().hex}",
            kind=kind,
            to_address=to,
            subject=subject,
            body_text=text,
            status=EmailOutbox.PENDING,
            attempts=0,
            max_attempts=MAX_ATTEMPTS,
            next_attempt_at=utcnow(),
            created_at=utcnow(),
        )
        .on_conflict_do_nothing(constraint="uq_email_outbox_dedup_key")
    )
    db.session.execute(statement)
    db.session.commit()
    if _worker is None and not current_app.testing:
        # gunicorn.conf.py starts the worker in each web worker; this covers
        # any other way of running the app (the development server).
        start_worker(current_app._get_current_object())
    wake_worker()


def _claim(now: datetime, limit: int) -> list[EmailOutbox]:
    rows = (
        db.session.execute(
            select(EmailOutbox)
            .where(
                EmailOutbox.status.in_((EmailOutbox.PENDING, EmailOutbox.SENDING)),
                EmailOutbox.next_attempt_at <= now,
                or_(EmailOutbox.locked_until.is_(None), EmailOutbox.locked_until < now),
            )
            .order_by(EmailOutbox.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        .scalars()
        .all()
    )
    for row in rows:
        row.status = EmailOutbox.SENDING
        row.locked_until = now + LEASE
        row.attempts += 1
    db.session.commit()
    return rows


def _send_one(row: EmailOutbox) -> str:
    try:
        send_email(to=row.to_address, subject=row.subject, text=row.body_text)
    except EmailSendError as exc:
        row.last_error = str(exc)[:255]
        row.locked_until = None
        if row.attempts >= row.max_attempts:
            row.status = EmailOutbox.FAILED
            logger.error(
                "Outbox email %s (%s) gave up after %s attempts: %s",
                row.id, row.kind, row.attempts, row.last_error,
            )
        else:
            row.status = EmailOutbox.PENDING
            row.next_attempt_at = utcnow() + retry_delay(row.attempts)
            logger.warning(
                "Outbox email %s (%s) attempt %s failed, retrying: %s",
                row.id, row.kind, row.attempts, row.last_error,
            )
    else:
        row.status = EmailOutbox.SENT
        row.sent_at = utcnow()
        row.locked_until = None
        row.last_error = None
    db.session.commit()
    return row.status


def _release(row: EmailOutbox) -> None:
    """Give back a row taken but not tried (the worker is stopping)."""
    row.status = EmailOutbox.PENDING
    row.locked_until = None
    row.attempts -= 1
    db.session.commit()


def process_due(limit: int = BATCH_SIZE, stopping: threading.Event | None = None) -> dict:
    """Send the due emails, at most ``limit``. Returns {status: count}.

    When ``stopping`` is set, the rows not tried yet go back to the queue.
    """
    done: dict[str, int] = {}
    for row in _claim(utcnow(), limit):
        if stopping is not None and stopping.is_set():
            _release(row)
            continue
        status = _send_one(row)
        done[status] = done.get(status, 0) + 1
    return done


def purge_done(now: datetime | None = None) -> int:
    """Delete sent and failed rows past their keeping time."""
    now = now or utcnow()
    result = db.session.execute(
        delete(EmailOutbox).where(
            or_(
                (EmailOutbox.status == EmailOutbox.SENT) & (EmailOutbox.created_at < now - KEEP_SENT),
                (EmailOutbox.status == EmailOutbox.FAILED) & (EmailOutbox.created_at < now - KEEP_FAILED),
            )
        )
    )
    db.session.commit()
    return result.rowcount


def counts() -> dict:
    """{status: rows}, plus the age in seconds of the oldest unsent row."""
    by_status = dict(
        db.session.execute(select(EmailOutbox.status, func.count()).group_by(EmailOutbox.status)).all()
    )
    oldest = db.session.execute(
        select(func.min(EmailOutbox.created_at)).where(
            EmailOutbox.status.in_((EmailOutbox.PENDING, EmailOutbox.SENDING))
        )
    ).scalar()
    by_status["oldest_unsent_seconds"] = int((utcnow() - oldest).total_seconds()) if oldest else 0
    return by_status


# --- The worker ---------------------------------------------------------------------------


class OutboxWorker:
    """A thread that sends due outbox emails for one web process.

    It is only the executor: the queue is the database, so a thread that is
    stopped or killed loses nothing.
    """

    def __init__(self, app, poll_seconds: float = POLL_SECONDS):
        self.app = app
        self.poll_seconds = poll_seconds
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_purge = 0.0

    def start(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, name="email-outbox", daemon=True)
            self._thread.start()

    def wake(self) -> None:
        self._wake.set()

    def stop(self, timeout: float = 10.0) -> bool:
        """Finish the email in hand and stop. False if it did not in time."""
        self._stop.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join(timeout)
            return not self._thread.is_alive()
        return True

    def _run(self) -> None:
        while not self._stop.is_set():
            busy = False
            try:
                with self.app.app_context():
                    try:
                        done = process_due(stopping=self._stop)
                        busy = sum(done.values()) >= BATCH_SIZE
                        self._maybe_purge()
                    finally:
                        db.session.remove()
            except Exception:  # never let one bad run end the thread
                logger.exception("Email outbox run failed")
            if not busy:
                self._wake.wait(self.poll_seconds)
                self._wake.clear()

    def _maybe_purge(self) -> None:
        now = utcnow().timestamp()
        if now - self._last_purge > 3600:
            self._last_purge = now
            purge_done()


_worker: OutboxWorker | None = None


def start_worker(app, poll_seconds: float = POLL_SECONDS) -> OutboxWorker:
    global _worker
    if _worker is None:
        _worker = OutboxWorker(app, poll_seconds)
        _worker.start()
    return _worker


def stop_worker(timeout: float = 10.0) -> bool:
    global _worker
    worker, _worker = _worker, None
    return worker.stop(timeout) if worker is not None else True


def wake_worker() -> None:
    if _worker is not None:
        _worker.wake()
