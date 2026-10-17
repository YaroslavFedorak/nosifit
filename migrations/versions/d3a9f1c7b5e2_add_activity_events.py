"""add activity events

Revision ID: d3a9f1c7b5e2
Revises: e4b8c2d6f1a3
Create Date: 2026-10-17 12:00:00.000000

A new table only: no existing row is read, changed or copied. It starts empty
and fills from the moment this release is deployed; earlier activity is not
reconstructed. Rows are deleted with their user.
"""
from alembic import op
import sqlalchemy as sa


revision = "d3a9f1c7b5e2"
down_revision = "e4b8c2d6f1a3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "activity_events",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("event", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=8), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "day", "event", "source"),
    )
    op.create_index(
        "ix_activity_events_day_user", "activity_events", ["day", "user_id"]
    )


def downgrade():
    op.drop_index("ix_activity_events_day_user", table_name="activity_events")
    op.drop_table("activity_events")
