from sqlalchemy.sql import func
from web.app import db


class RecoveryHabitLog(db.Model):
    __tablename__ = "recovery_habit_logs"

    id = db.Column(db.Integer, primary_key=True)

    user_habit_id = db.Column(
        db.Integer, db.ForeignKey("recovery_user_habits.id"), nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    date = db.Column(db.Date, nullable=False)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime(timezone=True))

    user = db.relationship("User", back_populates="recovery_habit_logs")
    user_habit = db.relationship("UserRecoveryHabit", back_populates="logs")
