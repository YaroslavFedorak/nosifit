from sqlalchemy.dialects.postgresql import JSONB

from backend.app.extensions import db


class MealItem(db.Model):
    __tablename__ = "meal_items"

    id = db.Column(db.Integer, primary_key=True)

    meal_id = db.Column(
        db.Integer,
        db.ForeignKey("meals.id"),
        nullable=False,
        index=True,
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("nutrition_products.id"),
        nullable=True,
        index=True,
    )

    name = db.Column(db.String(120), nullable=False)

    amount = db.Column(db.Float, nullable=True)
    unit = db.Column(db.String(8), nullable=True)

    # Legacy compatibility: this is the normalized gram amount.
    weight = db.Column(db.Float, nullable=True)

    # Nutrition values are a snapshot taken when the entry is written. Later
    # changes to the product (a user editing their own product, a catalog
    # correction) never touch logged entries. ``None`` means unknown.
    calories = db.Column(db.Integer, nullable=False, default=0)
    protein = db.Column(db.Float, nullable=False, default=0)
    fat = db.Column(db.Float, nullable=False, default=0)
    carbs = db.Column(db.Float, nullable=False, default=0)
    fiber = db.Column(db.Float, nullable=True)
    sugar = db.Column(db.Float, nullable=True)
    saturated_fat = db.Column(db.Float, nullable=True)
    salt = db.Column(db.Float, nullable=True)

    # The product's per-100 g values at the time of logging, so changing the
    # amount later rescales from the snapshot, not from the current product.
    # NULL on entries logged before snapshots existed.
    basis = db.Column(JSONB, nullable=True)

    # Set when the entry was added from a saved dish. The dish is only a
    # template: editing or deleting it never changes logged entries.
    dish_id = db.Column(
        db.Integer,
        db.ForeignKey("nutrition_dishes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    dish_name = db.Column(db.String(120), nullable=True)

    # Hydration contribution captured when this entry is calculated.
    liquid_ml = db.Column(
        db.Float,
        nullable=False,
        default=0,
    )

    category_id = db.Column(
        db.Integer,
        db.ForeignKey("categories.id"),
        nullable=True,
    )

    product = db.relationship(
        "Product",
        back_populates="entries",
    )

    def __repr__(self):
        return f"<MealItem id={self.id} meal_id={self.meal_id} name={self.name}>"
