"""link training sessions to the plan day they completed

Revision ID: a7c3e9d1f4b6
Revises: d3a9f1c7b5e2
Create Date: 2026-10-18 12:00:00.000000

Three nullable columns on training_sessions; no existing row is read or
changed. A session completed from a weekly plan records the plan, its weekday
and the calendar date it counts for, and a partial unique index allows one
such session per plan and date, so completing a day twice cannot duplicate it.
Deleting a plan keeps the sessions (plan_id becomes NULL): the workout was
done even if the plan is gone.
"""
from alembic import op
import sqlalchemy as sa


revision = "a7c3e9d1f4b6"
down_revision = "d3a9f1c7b5e2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("training_sessions", sa.Column("plan_id", sa.Integer(), nullable=True))
    op.add_column("training_sessions", sa.Column("plan_day", sa.String(length=3), nullable=True))
    op.add_column("training_sessions", sa.Column("plan_date", sa.Date(), nullable=True))
    op.create_foreign_key(
        "fk_training_sessions_plan_id",
        "training_sessions",
        "te_training_plans",
        ["plan_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "uq_training_sessions_plan_date",
        "training_sessions",
        ["plan_id", "plan_date"],
        unique=True,
        postgresql_where=sa.text("plan_id IS NOT NULL"),
    )


def downgrade():
    op.drop_index("uq_training_sessions_plan_date", table_name="training_sessions")
    op.drop_constraint("fk_training_sessions_plan_id", "training_sessions", type_="foreignkey")
    op.drop_column("training_sessions", "plan_date")
    op.drop_column("training_sessions", "plan_day")
    op.drop_column("training_sessions", "plan_id")
