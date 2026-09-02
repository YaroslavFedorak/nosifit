from sqlalchemy.sql import func
from web.app import db


class UserRecoveryHabit(db.Model):
    __tablename__ = "recovery_user_habits"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    habit_id = db.Column(
        db.Integer, db.ForeignKey("recovery_habits.id"), nullable=False
    )

    is_active = db.Column(db.Boolean, default=True)

    user = db.relationship("User", back_populates="recovery_habits")
    habit = db.relationship("RecoveryHabit", back_populates="users")

    logs = db.relationship(
        "RecoveryHabitLog",
        back_populates="user_habit",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
