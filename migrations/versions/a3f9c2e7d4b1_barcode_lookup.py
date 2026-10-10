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


def _global_barcode_uniques(bind):
    """(constraints, indexes) that make ``barcode`` alone globally unique.

    Found by inspection, not by name: 8c4e6f2a91b7 created an unnamed
    UniqueConstraint (PostgreSQL calls it nutrition_products_barcode_key),
    but a database built another way may use a different name, or a plain
    unique index.
    """
    inspector = sa.inspect(bind)
    constraints = [
        c["name"]
        for c in inspector.get_unique_constraints("nutrition_products")
        if c["column_names"] == ["barcode"]
    ]
    indexes = [
        i["name"]
        for i in inspector.get_indexes("nutrition_products")
        if i.get("unique")
        and i["column_names"] == ["barcode"]
        and not (i.get("dialect_options") or {}).get("postgresql_where")
        # PostgreSQL reports a constraint's backing index as an index too.
        and i["name"] not in constraints
    ]
    return constraints, indexes


def upgrade():
    bind = op.get_bind()
    constraints, indexes = _global_barcode_uniques(bind)
    for name in constraints:
        op.drop_constraint(name, "nutrition_products", type_="unique")
    for name in indexes:
        op.drop_index(name, table_name="nutrition_products")
    if any(_global_barcode_uniques(bind)):
        # Never continue with the old global rule still in place.
        raise RuntimeError("a global unique rule on nutrition_products.barcode remains")
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
