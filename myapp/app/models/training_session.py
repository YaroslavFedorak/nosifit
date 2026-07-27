from datetime import datetime
from myapp.app import db


class TrainingSession(db.Model):
    __tablename__ = "training_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    started_at = db.Column(db.DateTime)
    finished_at = db.Column(db.DateTime)
    status = db.Column(db.String(20))

    fatigue_before = db.Column(db.Integer)
    fatigue_after = db.Column(db.Integer)

    internal_load = db.Column(db.Float, default=0)
    muscle_loads = db.Column(db.JSON, default={})

    rpe_avg = db.Column(db.Float)

    user = db.relationship("User", back_populates="training_sessions")

    exercises = db.relationship(
        "SessionExercise", back_populates="session", cascade="all, delete-orphan"
    )


class SessionExercise(db.Model):
    __tablename__ = "session_exercises"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.Integer, db.ForeignKey("training_sessions.id"), nullable=False
    )

    exercise_id = db.Column(db.String(64), nullable=False)

    sets_planned = db.Column(db.Integer, nullable=True)
    sets_done = db.Column(db.Integer, default=0)

    reps_planned = db.Column(db.String(32), nullable=True)
    reps_done = db.Column(db.String(32))

    load_planned = db.Column(db.Float, nullable=True)
    load_done = db.Column(db.Float)

    rpe = db.Column(db.Float)

    session = db.relationship("TrainingSession", back_populates="exercises")
