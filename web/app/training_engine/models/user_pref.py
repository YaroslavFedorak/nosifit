from datetime import datetime
from web.app import db


class UserPreference(db.Model):
    __tablename__ = "te_user_preferences"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    key = db.Column(db.String(120), nullable=False)
    value = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    user = db.relationship("User", back_populates="preferences", foreign_keys=[user_id])

    def __repr__(self):
        return f"<UserPreference id={self.id} user_id={self.user_id} key={self.key}>"
