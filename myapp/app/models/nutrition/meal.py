from datetime import datetime

from myapp.app import db


class Meal(db.Model):
    __tablename__ = "meals"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    date = db.Column(
        db.Date,
        nullable=False,
    )

    time = db.Column(
        db.Time,
        nullable=True,
    )

    name = db.Column(
        db.String(120),
        nullable=False,
    )

    category = db.Column(
        db.String(50),
        nullable=False,
    )

    total_calories = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )

    total_protein = db.Column(
        db.Float,
        nullable=False,
        default=0,
    )

    total_fat = db.Column(
        db.Float,
        nullable=False,
        default=0,
    )

    total_carbs = db.Column(
        db.Float,
        nullable=False,
        default=0,
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

    user = db.relationship(
        "User",
        back_populates="meals",
    )

    items = db.relationship(
        "MealItem",
        backref="meal",
        lazy=True,
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return (
            f"<Meal " f"id={self.id} " f"user_id={self.user_id} " f"name={self.name}>"
        )
