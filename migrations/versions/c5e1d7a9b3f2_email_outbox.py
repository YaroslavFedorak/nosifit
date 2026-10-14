"""email outbox for notices sent in the background

Revision ID: c5e1d7a9b3f2
Revises: b8d4f1a6c3e9
Create Date: 2026-10-13 18:00:00.000000

Security notices (Telegram connected/disconnected, email changed) were sent
inside the request, with one attempt, and lost when the email service
failed. They are now written here and sent by a worker in the web process,
with retries. A new, empty table: nothing existing changes.
"""

from alembic import op
import sqlalchemy as sa


revision = "c5e1d7a9b3f2"
down_revision = "b8d4f1a6c3e9"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "email_outbox",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dedup_key", sa.String(length=128), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("to_address", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("dedup_key", name="uq_email_outbox_dedup_key"),
    )
    op.create_index(
        "ix_email_outbox_status_next_attempt_at",
        "email_outbox",
        ["status", "next_attempt_at"],
    )


def downgrade():
    op.drop_index("ix_email_outbox_status_next_attempt_at", table_name="email_outbox")
    op.drop_table("email_outbox")
