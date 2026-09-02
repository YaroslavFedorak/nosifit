from web.app import db


class SavedMeal(db.Model):
    __tablename__ = "saved_meals"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )

    name = db.Column(db.String(120), nullable=False)

    calories = db.Column(db.Integer, nullable=False, default=0)

    protein = db.Column(db.Float, nullable=False, default=0)

    fat = db.Column(db.Float, nullable=False, default=0)

    carbs = db.Column(db.Float, nullable=False, default=0)

    def __repr__(self):
        return (
            f"<SavedMeal "
            f"id={self.id} "
            f"user_id={self.user_id} "
            f"name={self.name}>"
        )
