"""add nutrition goal history

Revision ID: b7d2e4a8c1f6
Revises: c5e1d7a9b3f2
Create Date: 2026-10-15 12:00:00.000000

A new table only: no existing row is read, changed or copied. History starts
empty; days before a user's first row have no stored targets and are not
reconstructed.
"""
from alembic import op
import sqlalchemy as sa


revision = "b7d2e4a8c1f6"
down_revision = "c5e1d7a9b3f2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "nutrition_goal_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("calories", sa.Integer(), nullable=False),
        sa.Column("protein", sa.Float(), nullable=False),
        sa.Column("fat", sa.Float(), nullable=False),
        sa.Column("carbs", sa.Float(), nullable=False),
        sa.Column("fiber", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "effective_from", name="uq_nutrition_goal_history_day"
        ),
    )
    op.create_index(
        op.f("ix_nutrition_goal_history_user_id"),
        "nutrition_goal_history",
        ["user_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        op.f("ix_nutrition_goal_history_user_id"), table_name="nutrition_goal_history"
    )
    op.drop_table("nutrition_goal_history")
