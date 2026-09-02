from datetime import datetime, timezone
from web.app import db


class OAuthAccount(db.Model):
    __tablename__ = "oauth_accounts"

    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(50), nullable=False)  # google / github
    provider_user_id = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user = db.relationship("User", back_populates="oauth_accounts")

    def __repr__(self):
        return f"<OAuthAccount id={self.id} provider={self.provider} user_id={self.user_id}>"
