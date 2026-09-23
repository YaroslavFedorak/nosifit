"""add training session load fields

Revision ID: 0dec34ec765f
Revises: 30742736f6de
Create Date: 2026-09-23 12:26:43.088528

"""

from alembic import op
import sqlalchemy as sa

revision = "0dec34ec765f"
down_revision = "30742736f6de"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("training_sessions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("internal_load", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("muscle_loads", sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table("training_sessions", schema=None) as batch_op:
        batch_op.drop_column("muscle_loads")
        batch_op.drop_column("internal_load")
