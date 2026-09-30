"""add indexes for nutrition query hotspots

Revision ID: b4a7d1e8c2f0
Revises: 8c4e6f2a91b7
Create Date: 2026-09-30
"""

from alembic import op


revision = "b4a7d1e8c2f0"
down_revision = "d7f31c9a44b2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_meals_user_date_time_id",
        "meals",
        ["user_id", "date", "time", "id"],
        unique=False,
    )
    op.create_index(
        "ix_meal_items_meal_id_id",
        "meal_items",
        ["meal_id", "id"],
        unique=False,
    )
    op.create_index(
        "ix_nutrition_product_favorites_user_created_product",
        "nutrition_product_favorites",
        ["user_id", "created_at", "product_id"],
        unique=False,
    )

    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX ix_nutrition_product_names_name_trgm "
        "ON nutrition_product_names USING gin (name gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX ix_nutrition_products_brand_trgm "
        "ON nutrition_products USING gin (brand gin_trgm_ops)"
    )


def downgrade():
    op.execute(
        "DROP INDEX IF EXISTS ix_nutrition_products_brand_trgm"
    )
    op.execute(
        "DROP INDEX IF EXISTS ix_nutrition_product_names_name_trgm"
    )

    op.drop_index(
        "ix_nutrition_product_favorites_user_created_product",
        table_name="nutrition_product_favorites",
    )
    op.drop_index(
        "ix_meal_items_meal_id_id",
        table_name="meal_items",
    )
    op.drop_index(
        "ix_meals_user_date_time_id",
        table_name="meals",
    )
