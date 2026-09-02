from web.app import db


class RecoveryHabit(db.Model):
    __tablename__ = "recovery_habits"

    id = db.Column(db.Integer, primary_key=True)

    slug = db.Column(db.String(64), nullable=False, unique=True)
    name = db.Column(db.String(128), nullable=False, unique=True)
    description = db.Column(db.String(256))

    category = db.Column(db.String(64))
    icon = db.Column(db.String(64))

    points = db.Column(db.Integer, nullable=False, default=0)
    daily_log_limit = db.Column(db.Integer, nullable=False, default=1)
    estimated_minutes = db.Column(db.Integer, nullable=False, default=0)

    recommended_when = db.Column(db.JSON, nullable=False, default=list)

    premium_only = db.Column(db.Boolean, nullable=False, default=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_archived = db.Column(db.Boolean, nullable=False, default=False)

    users = db.relationship(
        "UserRecoveryHabit",
        back_populates="habit",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "slug": self.slug,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "points": self.points,
            "icon": self.icon,
            "daily_log_limit": self.daily_log_limit,
            "estimated_minutes": self.estimated_minutes,
            "recommended_when": self.recommended_when,
            "premium_only": self.premium_only,
            "sort_order": self.sort_order,
            "is_active": self.is_active,
            "is_archived": self.is_archived,
        }
