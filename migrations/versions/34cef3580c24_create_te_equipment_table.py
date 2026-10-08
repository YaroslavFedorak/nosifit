"""Create te_equipment table

Revision ID: 34cef3580c24
Revises: f448d3545e27
Create Date: 2026-06-22 16:35:25.513968

"""

from alembic import op

revision = "34cef3580c24"
down_revision = "f448d3545e27"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("te_exercise_equipment", schema=None) as batch_op:
        batch_op.create_foreign_key(None, "te_equipment", ["equipment_id"], ["id"])


def downgrade():
    with op.batch_alter_table("te_exercise_equipment", schema=None) as batch_op:
        batch_op.drop_constraint(None, type_="foreignkey")
