from datetime import datetime

from backend.app.extensions import db


class Product(db.Model):
    """A food with its nutrition values per 100 g.

    Every value is per 100 g of the product, including drinks: ``ml`` amounts
    are converted to grams through ``grams_per_unit`` (the density), so one
    basis covers every calculation.

    ``source`` says who owns the product: ``system`` (the NosiFit catalog,
    read-only for users) or ``user`` (owned by ``owner_user_id``).
    ``data_source`` and ``source_ref`` say where a system product's values come
    from (e.g. ``ciqual_2020`` / ``13039``).

    Sugar, fiber, saturated fat and salt are nullable: ``None`` means unknown,
    ``0`` means a known zero. They are never coerced into each other.
    """

    __tablename__ = "nutrition_products"

    id = db.Column(db.Integer, primary_key=True)

    owner_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    source = db.Column(
        db.String(20),
        nullable=False,
        default="system",
        index=True,
    )

    # Stable identifier of a system product in the seed dataset.
    key = db.Column(db.String(80), nullable=True)

    # Canonical name (lowercase, punctuation-folded) used for duplicate checks.
    normalized_name = db.Column(db.String(160), nullable=True)

    brand = db.Column(db.String(120), nullable=True)
    barcode = db.Column(db.String(32), nullable=True, unique=True)
    category = db.Column(db.String(32), nullable=False, default="other", index=True)

    kcal_per_100g = db.Column(db.Float, nullable=False, default=0)
    protein_per_100g = db.Column(db.Float, nullable=False, default=0)
    fat_per_100g = db.Column(db.Float, nullable=False, default=0)
    carbs_per_100g = db.Column(db.Float, nullable=False, default=0)
    fiber_per_100g = db.Column(db.Float, nullable=True)
    sugar_per_100g = db.Column(db.Float, nullable=True)
    saturated_fat_per_100g = db.Column(db.Float, nullable=True)
    salt_per_100g = db.Column(db.Float, nullable=True)

    data_source = db.Column(db.String(32), nullable=True)
    source_ref = db.Column(db.String(64), nullable=True)
    verified = db.Column(db.Boolean, nullable=False, default=False)

    # Milliliters of fluid represented by 100 g of the product.
    # Zero means the product does not contribute to the hydration total.
    liquid_ml_per_100g = db.Column(
        db.Float,
        nullable=False,
        default=0,
    )

    default_unit = db.Column(
        db.String(8),
        nullable=False,
        default="g",
    )

    grams_per_unit = db.Column(
        db.Float,
        nullable=False,
        default=1,
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    owner = db.relationship(
        "User",
        back_populates="nutrition_products",
    )

    names = db.relationship(
        "ProductName",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy=True,
    )

    favorites = db.relationship(
        "ProductFavorite",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    entries = db.relationship(
        "MealItem",
        back_populates="product",
        lazy="dynamic",
    )

    __table_args__ = (
        db.CheckConstraint(
            "(source = 'user') = (owner_user_id IS NOT NULL)",
            name="ck_nutrition_products_owner_matches_source",
        ),
        db.Index(
            "uq_nutrition_products_key",
            "key",
            unique=True,
            postgresql_where=db.text("key IS NOT NULL"),
        ),
        # A user cannot have two active products with the same name.
        db.Index(
            "uq_nutrition_products_owner_name",
            "owner_user_id",
            "normalized_name",
            unique=True,
            postgresql_where=db.text(
                "owner_user_id IS NOT NULL AND is_active"
            ),
        ),
    )

    def __repr__(self):
        return f"<Product id={self.id} source={self.source}>"
