"""add fiber goal to nutrition goals

Revision ID: d7f31c9a44b2
Revises: 8c4e6f2a91b7
Create Date: 2026-09-30 12:20:00
"""
from alembic import op
import sqlalchemy as sa

revision = "d7f31c9a44b2"
down_revision = "8c4e6f2a91b7"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("user_goals") as batch_op:
        batch_op.add_column(
            sa.Column(
                "fiber_goal",
                sa.Float(),
                nullable=False,
                server_default="30",
            )
        )


def downgrade():
    with op.batch_alter_table("user_goals") as batch_op:
        batch_op.drop_column("fiber_goal")
