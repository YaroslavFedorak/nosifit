from web.app import db
from datetime import datetime, timedelta, timezone


class VerificationCode(db.Model):
    __tablename__ = "verification_codes"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False)
    code = db.Column(db.String(6), nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def is_expired(self):
        return datetime.now(timezone.utc) > self.created_at + timedelta(minutes=10)
