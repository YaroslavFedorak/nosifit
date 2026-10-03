"""add nutrition product categories

Revision ID: e3b7c1d9a4f2
Revises: b4a7d1e8c2f0
Create Date: 2026-10-03
"""

from alembic import op
import sqlalchemy as sa


revision = "e3b7c1d9a4f2"
down_revision = "b4a7d1e8c2f0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "nutrition_products",
        sa.Column(
            "category",
            sa.String(length=32),
            nullable=False,
            server_default="other",
        ),
    )
    op.create_index(
        "ix_nutrition_products_category",
        "nutrition_products",
        ["category"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "ix_nutrition_products_category",
        table_name="nutrition_products",
    )
    op.drop_column("nutrition_products", "category")
