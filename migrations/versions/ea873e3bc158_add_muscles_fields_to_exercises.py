"""add muscles fields to exercises

Revision ID: ea873e3bc158
Revises: 3338bd4cd707
Create Date: 2026-07-06 16:15:23.095793
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "ea873e3bc158"
down_revision = "3338bd4cd707"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("te_exercises", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "muscles_primary",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "muscles_secondary",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            )
        )


def downgrade():
    with op.batch_alter_table("te_exercises", schema=None) as batch_op:
        batch_op.drop_column("muscles_secondary")
        batch_op.drop_column("muscles_primary")
