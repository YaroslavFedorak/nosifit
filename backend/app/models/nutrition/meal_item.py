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

    # Nutrition values are stored as a snapshot calculated from Product.
    calories = db.Column(db.Integer, nullable=False, default=0)
    protein = db.Column(db.Float, nullable=False, default=0)
    fat = db.Column(db.Float, nullable=False, default=0)
    carbs = db.Column(db.Float, nullable=False, default=0)
    fiber = db.Column(db.Float, nullable=False, default=0)

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
