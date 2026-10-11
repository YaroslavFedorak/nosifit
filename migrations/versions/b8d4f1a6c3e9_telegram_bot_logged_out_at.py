"""remember a /logout in the Telegram bot

Revision ID: b8d4f1a6c3e9
Revises: a3f9c2e7d4b1
Create Date: 2026-10-11 12:00:00.000000

The bot restores a linked user's session from telegram_identities after a
restart instead of asking them to log in again. A user who pressed /logout
in the bot must stay logged out across that restart, so the logout is
stored here. NULL: not logged out (every existing identity).
"""

from alembic import op
import sqlalchemy as sa


revision = "b8d4f1a6c3e9"
down_revision = "a3f9c2e7d4b1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "telegram_identities",
        sa.Column("bot_logged_out_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_column("telegram_identities", "bot_logged_out_at")
