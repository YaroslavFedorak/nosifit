from web.app import db


class UserProfile(db.Model):
    __tablename__ = "user_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True
    )

    # Core profile flags
    training_location = db.Column(db.String(32), nullable=False)  # home, gym, outdoor
    wants_nutrition = db.Column(db.Boolean, default=False)
    wants_recovery = db.Column(db.Boolean, default=False)

    onboarding_completed = db.Column(db.Boolean, default=False)

    # Physical data
    weight = db.Column(db.Float)
    height = db.Column(db.Float)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))

    # Activity & goals
    activity = db.Column(db.String(10))
    goal = db.Column(db.String(20))
    experience = db.Column(db.String(50))
    workouts_per_week = db.Column(db.Integer)

    user = db.relationship("User", backref=db.backref("profile", uselist=False))

    def __repr__(self):
        return f"<UserProfile id={self.id} user_id={self.user_id}>"
