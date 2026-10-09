"""nutrition catalog v2: sourced values, dishes, entry snapshots

- products: sugar / saturated fat / salt, nullable fiber (NULL = unknown),
  data source + reference, stable seed key, normalized name, ownership check,
  one active product per name for each user
- product names: normalized name with prefix (btree) and trigram (GIN)
  indexes; the old trigram index on the raw name is replaced
- meal entries: sugar / saturated fat / salt, a per-100 g snapshot and the
  dish an entry came from
- reusable dishes and their components

Existing user products never asked for fiber in Telegram and defaulted the web
field to 0, so their 0 g fiber (and that of the entries logged from them) is
"unknown", not a measured zero: it becomes NULL.

Revision ID: e7a2c5d9f1b3
Revises: d5e1f3a7b2c8
Create Date: 2026-10-09
"""

import re
import unicodedata

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "e7a2c5d9f1b3"
down_revision = "d5e1f3a7b2c8"
branch_labels = None
depends_on = None


# Frozen copy of backend.app.utils.name_normalization.normalize_name, so this
# migration keeps producing the same values if the app's version changes.
_APOSTROPHES = re.compile(r"['’ʼ`´‘]")
_SEPARATORS = re.compile(r"[^\w%]+")
_EXTRA = str.maketrans({"ł": "l", "ø": "o", "ß": "ss", "æ": "ae", "œ": "oe"})


def _normalize(value):
    if not value:
        return ""
    text = unicodedata.normalize("NFKD", value.casefold())
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.translate(_EXTRA)
    text = _APOSTROPHES.sub("", text)
    text = _SEPARATORS.sub(" ", text).replace("_", " ")
    return " ".join(text.split())


def _backfill_names(bind):
    rows = bind.execute(
        sa.text("SELECT id, name FROM nutrition_product_names")
    ).fetchall()
    for row_id, name in rows:
        bind.execute(
            sa.text(
                "UPDATE nutrition_product_names SET normalized_name = :n WHERE id = :id"
            ),
            {"n": _normalize(name)[:160], "id": row_id},
        )


def _backfill_user_products(bind):
    """Give user products a canonical name; rename clashing duplicates.

    A user may already have two active products with the same name. Rather
    than archiving one (and hiding it), the later ones get a " (2)" suffix.
    """
    rows = bind.execute(
        sa.text(
            """
            SELECT p.id, p.owner_user_id, p.is_active, min(n.name) AS name
            FROM nutrition_products p
            JOIN nutrition_product_names n ON n.product_id = p.id
            WHERE p.owner_user_id IS NOT NULL
            GROUP BY p.id, p.owner_user_id, p.is_active
            ORDER BY p.owner_user_id, p.is_active DESC, p.id
            """
        )
    ).fetchall()

    taken = set()
    for product_id, owner_id, is_active, name in rows:
        normalized = _normalize(name)[:150]
        candidate, suffix = normalized, 1
        # Only active products must be unique; archived ones keep their name.
        while is_active and (owner_id, candidate) in taken:
            suffix += 1
            candidate = f"{normalized} {suffix}"
        if is_active:
            taken.add((owner_id, candidate))

        if candidate != normalized:
            bind.execute(
                sa.text(
                    "UPDATE nutrition_product_names SET name = :name, "
                    "normalized_name = :n WHERE product_id = :id"
                ),
                {"name": f"{name[:150]} ({suffix})", "n": candidate, "id": product_id},
            )
        bind.execute(
            sa.text(
                "UPDATE nutrition_products SET normalized_name = :n WHERE id = :id"
            ),
            {"n": candidate, "id": product_id},
        )


def upgrade():
    bind = op.get_bind()

    # --- products -------------------------------------------------------
    with op.batch_alter_table("nutrition_products") as batch_op:
        batch_op.add_column(sa.Column("key", sa.String(80), nullable=True))
        batch_op.add_column(sa.Column("normalized_name", sa.String(160), nullable=True))
        batch_op.add_column(sa.Column("sugar_per_100g", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("saturated_fat_per_100g", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("salt_per_100g", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("data_source", sa.String(32), nullable=True))
        batch_op.add_column(sa.Column("source_ref", sa.String(64), nullable=True))
        batch_op.add_column(
            sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.alter_column("fiber_per_100g", existing_type=sa.Float(), nullable=True)

    # Ownership and source must agree before the check constraint goes on.
    op.execute(
        "UPDATE nutrition_products SET source = 'user' "
        "WHERE owner_user_id IS NOT NULL AND source <> 'user'"
    )
    op.execute(
        "UPDATE nutrition_products SET source = 'imported' "
        "WHERE owner_user_id IS NULL AND source = 'user'"
    )
    op.create_check_constraint(
        "ck_nutrition_products_owner_matches_source",
        "nutrition_products",
        "(source = 'user') = (owner_user_id IS NOT NULL)",
    )

    # --- product names --------------------------------------------------
    op.add_column(
        "nutrition_product_names",
        sa.Column("normalized_name", sa.String(160), nullable=True),
    )
    _backfill_names(bind)
    _backfill_user_products(bind)
    op.alter_column("nutrition_product_names", "normalized_name", nullable=False)

    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("DROP INDEX IF EXISTS ix_nutrition_product_names_name_trgm")
    op.create_index(
        "ix_nutrition_product_names_normalized_prefix",
        "nutrition_product_names",
        ["normalized_name"],
        postgresql_ops={"normalized_name": "text_pattern_ops"},
    )
    op.execute(
        "CREATE INDEX ix_nutrition_product_names_normalized_trgm "
        "ON nutrition_product_names USING gin (normalized_name gin_trgm_ops)"
    )

    op.create_index(
        "uq_nutrition_products_key",
        "nutrition_products",
        ["key"],
        unique=True,
        postgresql_where=sa.text("key IS NOT NULL"),
    )
    op.create_index(
        "uq_nutrition_products_owner_name",
        "nutrition_products",
        ["owner_user_id", "normalized_name"],
        unique=True,
        postgresql_where=sa.text("owner_user_id IS NOT NULL AND is_active"),
    )

    # --- dishes ---------------------------------------------------------
    op.create_table(
        "nutrition_dishes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("normalized_name", sa.String(160), nullable=False),
        sa.Column("use_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "normalized_name", name="uq_nutrition_dishes_user_name"),
    )
    op.execute(
        "CREATE INDEX ix_nutrition_dishes_user_last_used "
        "ON nutrition_dishes (user_id, last_used_at DESC NULLS LAST)"
    )

    op.create_table(
        "nutrition_dish_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "dish_id",
            sa.Integer(),
            sa.ForeignKey("nutrition_dishes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("nutrition_products.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(8), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("dish_id", "product_id", name="uq_nutrition_dish_items_dish_product"),
        sa.CheckConstraint("amount > 0", name="ck_nutrition_dish_items_amount_positive"),
    )
    op.create_index(
        "ix_nutrition_dish_items_product_id", "nutrition_dish_items", ["product_id"]
    )

    # --- meal entries ---------------------------------------------------
    with op.batch_alter_table("meal_items") as batch_op:
        batch_op.alter_column("fiber", existing_type=sa.Float(), nullable=True)
        batch_op.add_column(sa.Column("sugar", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("saturated_fat", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("salt", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("basis", postgresql.JSONB(), nullable=True))
        batch_op.add_column(sa.Column("dish_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("dish_name", sa.String(120), nullable=True))
        batch_op.create_foreign_key(
            "fk_meal_items_dish_id",
            "nutrition_dishes",
            ["dish_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_meal_items_dish_id", ["dish_id"])

    with op.batch_alter_table("meals") as batch_op:
        batch_op.alter_column("total_fiber", existing_type=sa.Float(), nullable=True)
        batch_op.add_column(sa.Column("total_sugar", sa.Float(), nullable=True))

    # --- fiber 0 -> unknown for user products ----------------------------
    op.execute(
        "UPDATE nutrition_products SET fiber_per_100g = NULL "
        "WHERE source = 'user' AND fiber_per_100g = 0"
    )
    # Two statements on purpose: within one statement (a data-modifying CTE)
    # the recount would still see the old 0 values.
    op.execute(
        """
        UPDATE meal_items mi SET fiber = NULL
        FROM nutrition_products p
        WHERE mi.product_id = p.id AND p.source = 'user'
          AND mi.fiber = 0 AND p.fiber_per_100g IS NULL
        """
    )
    op.execute(
        """
        UPDATE meals m
        SET total_fiber = (SELECT sum(fiber) FROM meal_items WHERE meal_id = m.id)
        WHERE m.id IN (
            SELECT mi.meal_id FROM meal_items mi
            JOIN nutrition_products p ON p.id = mi.product_id
            WHERE p.source = 'user' AND mi.fiber IS NULL
        )
        """
    )


def downgrade():
    op.execute(
        "UPDATE meals SET total_fiber = 0 WHERE total_fiber IS NULL"
    )
    with op.batch_alter_table("meals") as batch_op:
        batch_op.drop_column("total_sugar")
        batch_op.alter_column("total_fiber", existing_type=sa.Float(), nullable=False)

    op.execute("UPDATE meal_items SET fiber = 0 WHERE fiber IS NULL")
    with op.batch_alter_table("meal_items") as batch_op:
        batch_op.drop_index("ix_meal_items_dish_id")
        batch_op.drop_constraint("fk_meal_items_dish_id", type_="foreignkey")
        batch_op.drop_column("dish_name")
        batch_op.drop_column("dish_id")
        batch_op.drop_column("basis")
        batch_op.drop_column("salt")
        batch_op.drop_column("saturated_fat")
        batch_op.drop_column("sugar")
        batch_op.alter_column("fiber", existing_type=sa.Float(), nullable=False)

    op.drop_index("ix_nutrition_dish_items_product_id", table_name="nutrition_dish_items")
    op.drop_table("nutrition_dish_items")
    op.execute("DROP INDEX IF EXISTS ix_nutrition_dishes_user_last_used")
    op.drop_table("nutrition_dishes")

    op.drop_index("uq_nutrition_products_owner_name", table_name="nutrition_products")
    op.drop_index("uq_nutrition_products_key", table_name="nutrition_products")
    op.execute("DROP INDEX IF EXISTS ix_nutrition_product_names_normalized_trgm")
    op.drop_index(
        "ix_nutrition_product_names_normalized_prefix",
        table_name="nutrition_product_names",
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_nutrition_product_names_name_trgm "
        "ON nutrition_product_names USING gin (name gin_trgm_ops)"
    )
    op.drop_column("nutrition_product_names", "normalized_name")

    op.drop_constraint(
        "ck_nutrition_products_owner_matches_source",
        "nutrition_products",
        type_="check",
    )
    op.execute("UPDATE nutrition_products SET fiber_per_100g = 0 WHERE fiber_per_100g IS NULL")
    with op.batch_alter_table("nutrition_products") as batch_op:
        batch_op.alter_column("fiber_per_100g", existing_type=sa.Float(), nullable=False)
        batch_op.drop_column("verified")
        batch_op.drop_column("source_ref")
        batch_op.drop_column("data_source")
        batch_op.drop_column("salt_per_100g")
        batch_op.drop_column("saturated_fat_per_100g")
        batch_op.drop_column("sugar_per_100g")
        batch_op.drop_column("normalized_name")
        batch_op.drop_column("key")
