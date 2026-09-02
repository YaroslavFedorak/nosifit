from web.app import db


class NutritionPlan(db.Model):
    __tablename__ = "nutrition_plans"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True, index=True
    )

    calories = db.Column(db.Integer, nullable=False)

    protein = db.Column(db.Float, nullable=False)

    fats = db.Column(db.Float, nullable=False)

    carbs = db.Column(db.Float, nullable=False)

    user = db.relationship("User", back_populates="nutrition_plan")

    def __repr__(self):
        return (
            f"<NutritionPlan " f"user_id={self.user_id} " f"calories={self.calories}>"
        )
