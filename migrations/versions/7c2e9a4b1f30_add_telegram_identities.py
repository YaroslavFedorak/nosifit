"""add Telegram identities and one-time link tokens

Revision ID: 7c2e9a4b1f30
Revises: a9c3e5f7b1d2
Create Date: 2026-10-07 12:00:00.000000

Telegram becomes a sign-in identity of a user instead of a client that
types the user's email and password. The previous bot kept its logins in
process memory only, so there is no stored Telegram data to migrate: every
bot user connects their Telegram account once with the new flow.

- telegram_identities: Telegram numeric user id <-> NosiFit user, unique on
  both sides; removed together with the user (ON DELETE CASCADE).
- telegram_link_tokens: SHA-256 of one-time, short-lived link tokens.
"""

from alembic import op
import sqlalchemy as sa


revision = "7c2e9a4b1f30"
down_revision = "a9c3e5f7b1d2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "telegram_identities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_username", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_telegram_identities_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_telegram_identities_user_id"),
        sa.UniqueConstraint(
            "telegram_user_id", name="uq_telegram_identities_telegram_user_id"
        ),
    )

    op.create_table(
        "telegram_link_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_username", sa.String(length=64), nullable=True),
        sa.Column("telegram_name", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_telegram_link_tokens_token_hash"),
    )
    op.create_index(
        "ix_telegram_link_tokens_telegram_user_id",
        "telegram_link_tokens",
        ["telegram_user_id"],
    )
    op.create_index(
        "ix_telegram_link_tokens_expires_at",
        "telegram_link_tokens",
        ["expires_at"],
    )


def downgrade():
    op.drop_index("ix_telegram_link_tokens_expires_at", table_name="telegram_link_tokens")
    op.drop_index(
        "ix_telegram_link_tokens_telegram_user_id", table_name="telegram_link_tokens"
    )
    op.drop_table("telegram_link_tokens")
    op.drop_table("telegram_identities")
