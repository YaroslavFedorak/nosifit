from datetime import date

from myapp.app import db


class UserWater(db.Model):
    __tablename__ = "user_water"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )

    date = db.Column(db.Date, default=date.today, nullable=False)

    amount = db.Column(db.Float, nullable=False, default=0)

    __table_args__ = (
        db.UniqueConstraint("user_id", "date", name="uq_user_water_date"),
    )

    def __repr__(self):
        return (
            f"<UserWater "
            f"user_id={self.user_id} "
            f"date={self.date} "
            f"amount={self.amount}>"
        )
