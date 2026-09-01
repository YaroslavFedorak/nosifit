from myapp.app import db


class MealItem(db.Model):
    __tablename__ = "meal_items"

    id = db.Column(db.Integer, primary_key=True)

    meal_id = db.Column(
        db.Integer, db.ForeignKey("meals.id"), nullable=False, index=True
    )

    name = db.Column(db.String(120), nullable=False)

    weight = db.Column(db.Float, nullable=True)

    calories = db.Column(db.Integer, nullable=False, default=0)

    protein = db.Column(db.Float, nullable=False, default=0)
    fat = db.Column(db.Float, nullable=False, default=0)
    carbs = db.Column(db.Float, nullable=False, default=0)

    fiber = db.Column(db.Float, nullable=False, default=0)

    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)

    def __repr__(self):
        return (
            f"<MealItem id={self.id} " f"meal_id={self.meal_id} " f"name={self.name}>"
        )
