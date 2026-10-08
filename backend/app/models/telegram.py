"""Telegram as a sign-in identity of a NosiFit user.

The canonical identity is Telegram's numeric user id. Usernames change and
can be taken over by someone else, so they are stored only for display.
Nothing secret from Telegram (bot token, login hash) is kept here.
"""

from datetime import datetime, timezone

from backend.app.extensions import db


def _utcnow():
    return datetime.now(timezone.utc)


class TelegramIdentity(db.Model):
    __tablename__ = "telegram_identities"
    __table_args__ = (
        db.UniqueConstraint("user_id", name="uq_telegram_identities_user_id"),
        db.UniqueConstraint(
            "telegram_user_id", name="uq_telegram_identities_telegram_user_id"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    # One NosiFit user has at most one Telegram account and vice versa.
    user_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "users.id",
            name="fk_telegram_identities_user_id_users",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    telegram_user_id = db.Column(db.BigInteger, nullable=False)
    telegram_username = db.Column(db.String(64), nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )
    last_login_at = db.Column(db.DateTime(timezone=True), nullable=True)

    user = db.relationship("User", back_populates="telegram_identity")

    def __repr__(self):
        return f"<TelegramIdentity id={self.id} user_id={self.user_id}>"


class TelegramLinkToken(db.Model):
    """One-time link that connects a Telegram account to a signed-in user.

    Only a SHA-256 of the token is stored; the token itself exists in the
    bot's message and the browser that opens it.
    """

    __tablename__ = "telegram_link_tokens"
    __table_args__ = (
        db.UniqueConstraint("token_hash", name="uq_telegram_link_tokens_token_hash"),
    )

    id = db.Column(db.Integer, primary_key=True)
    token_hash = db.Column(db.String(64), nullable=False)
    telegram_user_id = db.Column(db.BigInteger, nullable=False, index=True)
    # Shown on the confirmation page so the user sees which Telegram account
    # is about to get access.
    telegram_username = db.Column(db.String(64), nullable=True)
    telegram_name = db.Column(db.String(128), nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), default=_utcnow, nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    used_at = db.Column(db.DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<TelegramLinkToken id={self.id}>"
