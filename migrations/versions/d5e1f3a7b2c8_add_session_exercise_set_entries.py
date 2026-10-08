"""add per-set entries to session exercises

Each set of a logged exercise keeps its own reps (or seconds) and kg. The
per-exercise columns stay and are derived from the sets, so the training
model reads them unchanged.

Revision ID: d5e1f3a7b2c8
Revises: c4d8e2f6a1b9
Create Date: 2026-10-09
"""

import sqlalchemy as sa
from alembic import op

revision = "d5e1f3a7b2c8"
down_revision = "c4d8e2f6a1b9"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("session_exercises", schema=None) as batch_op:
        batch_op.add_column(sa.Column("set_entries", sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table("session_exercises", schema=None) as batch_op:
        batch_op.drop_column("set_entries")
