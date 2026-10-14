"""Emails waiting to be sent by the outbox worker (backend/app/services/email_outbox.py).

A row is written in the request; the worker sends it, retries failures with
a growing delay and marks it sent or, after max_attempts, failed. Rows are
deleted some days after they are done, so addresses do not pile up here.
"""

from datetime import datetime, timezone

from backend.app.extensions import db


def _utcnow():
    return datetime.now(timezone.utc)


class EmailOutbox(db.Model):
    __tablename__ = "email_outbox"
    __table_args__ = (
        db.UniqueConstraint("dedup_key", name="uq_email_outbox_dedup_key"),
        # The worker's query: due rows that are not taken.
        db.Index("ix_email_outbox_status_next_attempt_at", "status", "next_attempt_at"),
    )

    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"

    id = db.Column(db.Integer, primary_key=True)
    # The same key is enqueued once; a retried request cannot add a duplicate.
    dedup_key = db.Column(db.String(128), nullable=False)
    kind = db.Column(db.String(64), nullable=False)
    to_address = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    body_text = db.Column(db.Text, nullable=False)

    status = db.Column(db.String(16), nullable=False, default=PENDING)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    max_attempts = db.Column(db.Integer, nullable=False, default=6)
    next_attempt_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    # A worker that took the row and died leaves it "sending"; once this
    # passes, another worker may take it again.
    locked_until = db.Column(db.DateTime(timezone=True), nullable=True)
    last_error = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    sent_at = db.Column(db.DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<EmailOutbox id={self.id} kind={self.kind} status={self.status}>"
