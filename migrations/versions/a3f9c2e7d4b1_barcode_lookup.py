"""barcode lookup: per-owner barcode uniqueness and external lookup cache

- products: the global UNIQUE(barcode) becomes two partial unique indexes,
  one for the shared catalog (owner_user_id IS NULL) and one per user for
  active own products. A user's private product with a barcode can then
  neither block a catalog import of that barcode nor reveal that it exists.
- nutrition_barcode_lookups: confirmed answers ("found" / "not found") of
  the external product database, by canonical barcode, with an expiry.
  Temporary failures are never stored.

Revision ID: a3f9c2e7d4b1
Revises: e7a2c5d9f1b3
Create Date: 2026-10-10
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "a3f9c2e7d4b1"
down_revision = "e7a2c5d9f1b3"
branch_labels = None
depends_on = None


def upgrade():
    # PostgreSQL's default name for the unnamed UniqueConstraint("barcode")
    # of 8c4e6f2a91b7.
    op.execute(
        "ALTER TABLE nutrition_products "
        "DROP CONSTRAINT IF EXISTS nutrition_products_barcode_key"
    )
    op.create_index(
        "uq_nutrition_products_catalog_barcode",
        "nutrition_products",
        ["barcode"],
        unique=True,
        postgresql_where=sa.text("owner_user_id IS NULL AND barcode IS NOT NULL"),
    )
    op.create_index(
        "uq_nutrition_products_owner_barcode",
        "nutrition_products",
        ["owner_user_id", "barcode"],
        unique=True,
        postgresql_where=sa.text(
            "owner_user_id IS NOT NULL AND barcode IS NOT NULL AND is_active"
        ),
    )

    op.create_table(
        "nutrition_barcode_lookups",
        sa.Column("barcode", sa.String(14), primary_key=True),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('found', 'not_found')",
            name="ck_nutrition_barcode_lookups_status",
        ),
    )
    op.create_index(
        "ix_nutrition_barcode_lookups_expires_at",
        "nutrition_barcode_lookups",
        ["expires_at"],
    )


def downgrade():
    op.drop_index(
        "ix_nutrition_barcode_lookups_expires_at",
        table_name="nutrition_barcode_lookups",
    )
    op.drop_table("nutrition_barcode_lookups")

    op.drop_index("uq_nutrition_products_owner_barcode", table_name="nutrition_products")
    op.drop_index("uq_nutrition_products_catalog_barcode", table_name="nutrition_products")
    # User products may now share a barcode with the catalog; the global
    # constraint cannot come back while they do, so theirs are cleared.
    op.execute(
        """
        UPDATE nutrition_products p SET barcode = NULL
        WHERE p.owner_user_id IS NOT NULL AND p.barcode IS NOT NULL
          AND EXISTS (
            SELECT 1 FROM nutrition_products o
            WHERE o.barcode = p.barcode AND o.id <> p.id
              AND (o.owner_user_id IS NULL OR o.id < p.id)
          )
        """
    )
    op.create_unique_constraint(
        "nutrition_products_barcode_key", "nutrition_products", ["barcode"]
    )
