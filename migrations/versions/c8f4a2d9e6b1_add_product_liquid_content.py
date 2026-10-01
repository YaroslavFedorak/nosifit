"""add liquid content to nutrition products and entries

Revision ID: c8f4a2d9e6b1
Revises: b4a7d1e8c2f0
Create Date: 2026-10-01
"""

from alembic import op
import sqlalchemy as sa


revision = "c8f4a2d9e6b1"
down_revision = "b4a7d1e8c2f0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "nutrition_products",
        sa.Column(
            "liquid_ml_per_100g",
            sa.Float(),
            nullable=False,
            server_default="0",
        ),
    )

    op.add_column(
        "meal_items",
        sa.Column(
            "liquid_ml",
            sa.Float(),
            nullable=False,
            server_default="0",
        ),
    )

    # Backfill the beverage products that already exist in the seed set.
    op.execute(
        """
        UPDATE nutrition_products
        SET liquid_ml_per_100g = 100
        WHERE id IN (
            SELECT product_id
            FROM nutrition_product_names
            WHERE locale = 'en'
              AND name IN (
                  'Water',
                  'Black coffee',
                  'Black tea',
                  'Milk 2.5%',
                  'Milk 1.5%'
              )
        )
        """
    )

    # Recalculate hydration for historical beverage entries as well.
    op.execute(
        """
        UPDATE meal_items
        SET liquid_ml = (
            nutrition_products.liquid_ml_per_100g
            * COALESCE(meal_items.weight, 0)
            / NULLIF(nutrition_products.grams_per_unit, 0)
            / 100.0
        )
        FROM nutrition_products
        WHERE meal_items.product_id = nutrition_products.id
        """
    )

    op.alter_column(
        "nutrition_products",
        "liquid_ml_per_100g",
        server_default=None,
    )

    op.alter_column(
        "meal_items",
        "liquid_ml",
        server_default=None,
    )


def downgrade():
    op.drop_column("meal_items", "liquid_ml")
    op.drop_column("nutrition_products", "liquid_ml_per_100g")
