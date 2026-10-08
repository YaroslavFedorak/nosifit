"""add nutrition product catalog

Revision ID: 8c4e6f2a91b7
Revises: 78213daccdf5
Create Date: 2026-09-30 11:30:00
"""
from alembic import op
import sqlalchemy as sa


revision = "8c4e6f2a91b7"
down_revision = "78213daccdf5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "nutrition_products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="system"),
        sa.Column("brand", sa.String(length=120), nullable=True),
        sa.Column("barcode", sa.String(length=32), nullable=True),
        sa.Column("kcal_per_100g", sa.Float(), nullable=False, server_default="0"),
        sa.Column("protein_per_100g", sa.Float(), nullable=False, server_default="0"),
        sa.Column("fat_per_100g", sa.Float(), nullable=False, server_default="0"),
        sa.Column("carbs_per_100g", sa.Float(), nullable=False, server_default="0"),
        sa.Column("fiber_per_100g", sa.Float(), nullable=False, server_default="0"),
        sa.Column("default_unit", sa.String(length=8), nullable=False, server_default="g"),
        sa.Column("grams_per_unit", sa.Float(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("barcode"),
    )
    op.create_index(
        "ix_nutrition_products_owner_user_id",
        "nutrition_products",
        ["owner_user_id"],
    )
    op.create_index(
        "ix_nutrition_products_source",
        "nutrition_products",
        ["source"],
    )
    op.create_index(
        "ix_nutrition_products_is_active",
        "nutrition_products",
        ["is_active"],
    )

    op.create_table(
        "nutrition_product_names",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("locale", sa.String(length=10), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["nutrition_products.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "product_id",
            "locale",
            name="uq_nutrition_product_name_locale",
        ),
    )
    op.create_index(
        "ix_nutrition_product_names_product_id",
        "nutrition_product_names",
        ["product_id"],
    )
    op.create_index(
        "ix_nutrition_product_names_locale",
        "nutrition_product_names",
        ["locale"],
    )
    op.create_index(
        "ix_nutrition_product_names_name",
        "nutrition_product_names",
        ["name"],
    )

    op.create_table(
        "nutrition_product_favorites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["nutrition_products.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "product_id",
            name="uq_nutrition_product_favorite",
        ),
    )
    op.create_index(
        "ix_nutrition_product_favorites_user_id",
        "nutrition_product_favorites",
        ["user_id"],
    )
    op.create_index(
        "ix_nutrition_product_favorites_product_id",
        "nutrition_product_favorites",
        ["product_id"],
    )

    with op.batch_alter_table("meals") as batch_op:
        batch_op.add_column(
            sa.Column("total_fiber", sa.Float(), nullable=False, server_default="0")
        )

    with op.batch_alter_table("meal_items") as batch_op:
        batch_op.add_column(
            sa.Column("product_id", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("amount", sa.Float(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("unit", sa.String(length=8), nullable=True)
        )
        batch_op.create_index(
            "ix_meal_items_product_id",
            ["product_id"],
            unique=False,
        )
        batch_op.create_foreign_key(
            "fk_meal_items_product_id",
            "nutrition_products",
            ["product_id"],
            ["id"],
        )

    op.execute(
        "UPDATE meal_items SET amount = weight, unit = 'g' "
        "WHERE amount IS NULL AND weight IS NOT NULL"
    )


def downgrade():
    with op.batch_alter_table("meal_items") as batch_op:
        batch_op.drop_constraint(
            "fk_meal_items_product_id",
            type_="foreignkey",
        )
        batch_op.drop_index("ix_meal_items_product_id")
        batch_op.drop_column("unit")
        batch_op.drop_column("amount")
        batch_op.drop_column("product_id")

    with op.batch_alter_table("meals") as batch_op:
        batch_op.drop_column("total_fiber")

    op.drop_table("nutrition_product_favorites")
    op.drop_table("nutrition_product_names")
    op.drop_table("nutrition_products")
