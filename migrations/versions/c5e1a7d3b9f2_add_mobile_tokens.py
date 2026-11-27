"""add sign-in tokens of the mobile apps

Revision ID: c5e1a7d3b9f2
Revises: f2b8d6a4c0e1
Create Date: 2026-11-27 12:00:00.000000

The Android and iOS apps sign in once with email and password and then send
a bearer token instead of a session cookie. Only the SHA-256 of a token is
stored, bound to the password fingerprint like browser sessions, and removed
together with the user (ON DELETE CASCADE).
"""

from alembic import op
import sqlalchemy as sa


revision = "c5e1a7d3b9f2"
down_revision = "f2b8d6a4c0e1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "mobile_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("fingerprint", sa.String(length=32), nullable=False),
        sa.Column("platform", sa.String(length=16), nullable=False),
        sa.Column("device_name", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_mobile_tokens_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_mobile_tokens_token_hash"),
    )
    op.create_index("ix_mobile_tokens_user_id", "mobile_tokens", ["user_id"])


def downgrade():
    op.drop_index("ix_mobile_tokens_user_id", table_name="mobile_tokens")
    op.drop_table("mobile_tokens")
