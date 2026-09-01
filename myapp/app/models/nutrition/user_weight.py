from myapp.app import db


class UserWeight(db.Model):
    __tablename__ = "user_weight_history"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )

    weight = db.Column(db.Float, nullable=False)

    date = db.Column(db.Date, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "date", name="uq_user_weight_date"),
    )

    def __repr__(self):
        return (
            f"<UserWeight "
            f"user_id={self.user_id} "
            f"date={self.date} "
            f"weight={self.weight}>"
        )
