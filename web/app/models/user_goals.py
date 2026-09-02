from web.app import db


class UserTrainingGoals(db.Model):
    __tablename__ = "user_training_goals"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True
    )

    primary_goal = db.Column(
        db.String(32), nullable=False
    )  # strength, endurance, fat_loss
    focus_upper = db.Column(db.Integer, default=5)  # 0–10
    focus_lower = db.Column(db.Integer, default=5)
    focus_core = db.Column(db.Integer, default=5)

    user = db.relationship("User", backref=db.backref("training_goals", uselist=False))
