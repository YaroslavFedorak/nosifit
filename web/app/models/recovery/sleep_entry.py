from sqlalchemy.sql import func
from web.app import db
from sqlalchemy import CheckConstraint


class SleepEntry(db.Model):
    __tablename__ = "recovery_sleep_entries"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user = db.relationship("User", back_populates="sleep_entries")

    sleep_start = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    sleep_end = db.Column(db.DateTime(timezone=True), nullable=False, index=True)

    duration_minutes = db.Column(db.Integer, nullable=False)
    quality_score = db.Column(db.Integer, nullable=False, default=0)

    created_at = db.Column(
        db.DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        db.Index("idx_sleep_user_date", "user_id", "sleep_start"),
        CheckConstraint(
            "duration_minutes BETWEEN 1 AND 1440", name="ck_sleep_duration_range"
        ),
        CheckConstraint(
            "quality_score BETWEEN 0 AND 100", name="ck_sleep_quality_range"
        ),
        CheckConstraint("sleep_end > sleep_start", name="ck_sleep_time_order"),
    )

    @property
    def duration_hours(self):
        return round(self.duration_minutes / 60, 1)
