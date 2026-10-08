"""repair historical liquid values after the initial hydration migration

Revision ID: d1a6c4e9b7f2
Revises: c8f4a2d9e6b1
Create Date: 2026-10-02
"""

from alembic import op


revision = "d1a6c4e9b7f2"
down_revision = "c8f4a2d9e6b1"
branch_labels = None
depends_on = None


HISTORICAL_LIQUID_FIX_SQL = """
UPDATE meal_items
SET liquid_ml = (
    nutrition_products.liquid_ml_per_100g
    * COALESCE(meal_items.weight, 0)
    / 100.0
)
FROM nutrition_products
WHERE meal_items.product_id = nutrition_products.id
"""


def upgrade():
    # meal_items.weight is already the normalized gram amount.
    op.execute(HISTORICAL_LIQUID_FIX_SQL)


def downgrade():
    pass
