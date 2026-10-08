from datetime import datetime
from flask_login import UserMixin
from backend.app.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash

from backend.app.utils.session_auth import make_session_id

# Accounts created through Google/GitHub/Telegram have no password. The
# column stores this marker instead of a hash; a password can be set later
# through the emailed reset link.
OAUTH_PASSWORD_MARKER = "oauth"


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    is_premium = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    age = db.Column(db.Integer, nullable=True)
    sex = db.Column(db.String(20), default="unspecified")
    weight = db.Column(db.Float, nullable=True)
    height = db.Column(db.Float, nullable=True)

    activity = db.Column(db.String(50), nullable=True)
    goal = db.Column(db.String(50), default="maintenance")
    experience = db.Column(db.String(50), default="beginner")
    workouts_per_week = db.Column(db.Integer, default=3)
    environment = db.Column(db.String(50), default="gym")

    weak_points = db.Column(db.JSON, default=list)
    strong_points = db.Column(db.JSON, default=list)

    fatigue_state_id = db.Column(db.Integer, db.ForeignKey("te_fatigue_state.id"))

    fatigue_state = db.relationship(
        "FatigueState", back_populates="user", uselist=False
    )

    nutrition_plan = db.relationship(
        "NutritionPlan",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    nutrition_products = db.relationship(
        "Product",
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="dynamic",
        foreign_keys="Product.owner_user_id",
    )

    nutrition_favorites = db.relationship(
        "ProductFavorite",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
        foreign_keys="ProductFavorite.user_id",
    )

    sleep_entries = db.relationship(
        "SleepEntry",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
        foreign_keys="SleepEntry.user_id",
    )

    recovery_habits = db.relationship(
        "UserRecoveryHabit",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
        foreign_keys="UserRecoveryHabit.user_id",
    )

    recovery_habit_logs = db.relationship(
        "RecoveryHabitLog",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
        foreign_keys="RecoveryHabitLog.user_id",
    )

    daily_recovery_snapshots = db.relationship(
        "DailyRecoverySnapshot",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
        foreign_keys="DailyRecoverySnapshot.user_id",
    )

    user_equipment = db.relationship(
        "UserEquipment",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
        foreign_keys="UserEquipment.user_id",
    )

    meals = db.relationship(
        "Meal",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
        foreign_keys="Meal.user_id",
    )

    oauth_accounts = db.relationship(
        "OAuthAccount",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
        foreign_keys="OAuthAccount.user_id",
    )

    telegram_identity = db.relationship(
        "TelegramIdentity",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    training_plans = db.relationship(
        "TrainingPlan",
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="dynamic",
        foreign_keys="TrainingPlan.user_id",
    )

    training_sessions = db.relationship(
        "TrainingSession",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
        foreign_keys="TrainingSession.user_id",
    )

    preferences = db.relationship(
        "UserPreference",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
        foreign_keys="UserPreference.user_id",
    )

    performance_states = db.relationship(
        "PerformanceState",
        back_populates="user",
        lazy="dynamic",
        cascade="all, delete-orphan",
        foreign_keys="PerformanceState.user_id",
    )

    def get_id(self):
        # "<id>:<password fingerprint>": see backend.app.utils.session_auth.
        return make_session_id(self)

    @property
    def has_password(self) -> bool:
        return bool(self.password) and self.password != OAUTH_PASSWORD_MARKER

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        if not self.has_password or not password:
            return False
        try:
            return check_password_hash(self.password, password)
        except ValueError:  # not a werkzeug hash
            return False

    def __repr__(self):
        return f"<User id={self.id} username={self.username}>"
