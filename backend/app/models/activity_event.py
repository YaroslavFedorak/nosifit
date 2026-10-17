from datetime import date

from backend.app.extensions import db


class ActivityEvent(db.Model):
    """One row per user, UTC day, event type and source: "the user did X today".

    Written only when a meaningful action succeeds (a meal, a workout, a
    sleep entry ...), never for page views or background requests, and
    deduplicated by the primary key. It holds no content of the action: no
    food, weights, text, IP or tokens. Rows start at the moment tracking was
    deployed; earlier activity is not reconstructed.
    """

    __tablename__ = "activity_events"

    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    day = db.Column(db.Date, primary_key=True, default=date.today)
    event = db.Column(db.String(32), primary_key=True)
    # "web" or "telegram": whether the action came through a Telegram session.
    source = db.Column(db.String(8), primary_key=True, default="web")

    __table_args__ = (db.Index("ix_activity_events_day_user", "day", "user_id"),)
