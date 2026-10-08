"""drop not null from planned columns

Revision ID: c1ef8f8b5a2b
Revises: b01de2483250
Create Date: 2026-07-08 15:09:54.168313

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c1ef8f8b5a2b"
down_revision = "b01de2483250"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("session_exercises", "sets_planned", nullable=True)
    op.alter_column("session_exercises", "reps_planned", nullable=True)
    op.alter_column("session_exercises", "load_planned", nullable=True)


def downgrade():
    pass
