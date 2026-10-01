from datetime import datetime

from backend.app.extensions import db


class Product(db.Model):
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

    brand = db.Column(db.String(120), nullable=True)
    barcode = db.Column(db.String(32), nullable=True, unique=True)

    kcal_per_100g = db.Column(db.Float, nullable=False, default=0)
    protein_per_100g = db.Column(db.Float, nullable=False, default=0)
    fat_per_100g = db.Column(db.Float, nullable=False, default=0)
    carbs_per_100g = db.Column(db.Float, nullable=False, default=0)
    fiber_per_100g = db.Column(db.Float, nullable=False, default=0)

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

    def __repr__(self):
        return f"<Product id={self.id} source={self.source}>"
