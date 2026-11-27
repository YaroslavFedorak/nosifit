"""Sign-in tokens of the NosiFit mobile apps (Android and iOS).

A mobile app signs in with email and password once and then sends
``Authorization: Bearer <token>`` with every API request. Only a SHA-256 of
the token is stored; the token itself lives in the phone's secure storage
(Android Keystore / iOS Keychain).

A token stops working when:
- the user signs out in the app (the row is deleted);
- it expires (``expires_at``);
- the password changes: ``fingerprint`` is the session fingerprint of the
  password hash at sign-in, exactly as browser sessions are bound to it
  (backend/app/utils/session_auth.py);
- the account is deleted (ON DELETE CASCADE).
"""

from datetime import datetime, timezone

from backend.app.extensions import db


def _utcnow():
    return datetime.now(timezone.utc)


class MobileToken(db.Model):
    __tablename__ = "mobile_tokens"
    __table_args__ = (
        db.UniqueConstraint("token_hash", name="uq_mobile_tokens_token_hash"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", name="fk_mobile_tokens_user_id_users", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash = db.Column(db.String(64), nullable=False)
    fingerprint = db.Column(db.String(32), nullable=False)
    # "android" or "ios", and a device label the app sends ("Pixel 8").
    # Shown later in the list of signed-in devices; never used for access.
    platform = db.Column(db.String(16), nullable=False)
    device_name = db.Column(db.String(64), nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), default=_utcnow, nullable=False)
    last_used_at = db.Column(db.DateTime(timezone=True), nullable=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)

    user = db.relationship(
        "User",
        backref=db.backref("mobile_tokens", lazy="dynamic", cascade="all, delete-orphan", passive_deletes=True),
    )

    def __repr__(self):
        return f"<MobileToken id={self.id} user_id={self.user_id} platform={self.platform}>"
