"""convert exercise json to jsonb

Revision ID: b01de2483250
Revises: e935a13882a5
Create Date: 2026-07-08 14:45:57.983706

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "b01de2483250"
down_revision = "e935a13882a5"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "te_exercises",
        "muscles_primary",
        type_=postgresql.JSONB(),
        postgresql_using="muscles_primary::jsonb",
    )
    op.alter_column(
        "te_exercises",
        "muscles_secondary",
        type_=postgresql.JSONB(),
        postgresql_using="muscles_secondary::jsonb",
    )
    op.alter_column(
        "te_exercises",
        "equipment",
        type_=postgresql.JSONB(),
        postgresql_using="equipment::jsonb",
    )
    op.alter_column(
        "te_exercises",
        "muscle_load_profile",
        type_=postgresql.JSONB(),
        postgresql_using="muscle_load_profile::jsonb",
    )


def downgrade():
    pass
