"""Deleting an account together with all personal data it owns."""

from sqlalchemy import delete, select, update

from backend.app.extensions import db
from backend.app.models.nutrition.category import Category
from backend.app.models.nutrition.goal_history import NutritionGoalHistory
from backend.app.models.nutrition.meal_item import MealItem
from backend.app.models.nutrition.saved_meal import SavedMeal
from backend.app.models.nutrition.user_goals import UserGoals
from backend.app.models.nutrition.user_water import UserWater
from backend.app.models.nutrition.user_weight import UserWeight
from backend.app.models.telegram import TelegramIdentity
from backend.app.models.user_goals import UserTrainingGoals
from backend.app.models.user_injury import UserInjury
from backend.app.models.user_profile import UserProfile
from backend.app.models.verification_code import VerificationCode

# Tables with a users.id foreign key that the User model does not cascade.
# Without this the final DELETE fails on a foreign key (or, for backref
# relationships, on NOT NULL) and the account can never be removed.
_UNCASCADED = (
    UserWater,
    UserWeight,
    UserGoals,
    NutritionGoalHistory,
    SavedMeal,
    UserInjury,
    UserTrainingGoals,
    UserProfile,
    # Also ON DELETE CASCADE in the database; deleted here explicitly so a
    # deleted account can never keep a Telegram sign-in.
    TelegramIdentity,
)


def delete_user_account(user) -> None:
    """Delete ``user`` and every row that belongs to them, in one transaction."""
    user_id = user.id
    email = user.email

    try:
        category_ids = select(Category.id).where(Category.user_id == user_id)
        db.session.execute(
            update(MealItem)
            .where(MealItem.category_id.in_(category_ids))
            .values(category_id=None)
        )
        db.session.execute(delete(Category).where(Category.user_id == user_id))

        for model in _UNCASCADED:
            db.session.execute(delete(model).where(model.user_id == user_id))

        db.session.execute(
            delete(VerificationCode).where(db.func.lower(VerificationCode.email) == email.lower())
        )

        # Rows deleted above must not linger in the identity map, or the ORM
        # would try to null their user_id when the user goes.
        db.session.expire_all()
        db.session.delete(db.session.get(type(user), user_id))
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


# --- Withdrawing consent -----------------------------------------------------------

# Kept when consent is withdrawn: the account itself (contract) and the ways
# to sign in, so the user can come back or delete the account. Everything
# else exists only because of the consent and is erased.
_KEPT_RELATIONSHIPS = {"oauth_accounts", "telegram_identity"}
_KEPT_TABLES = {"users", "oauth_accounts", "telegram_identities", "user_profiles"}
_USER_HEALTH_COLUMNS = (
    "age",
    "sex",
    "weight",
    "height",
    "activity",
    "goal",
    "experience",
    "workouts_per_week",
    "environment",
    "weak_points",
    "strong_points",
)


def withdraw_consent(user) -> None:
    """Withdraw the health-data consent: erase what it covered, keep the account.

    Health and fitness records (and the analytics events about them) are
    processed only on that consent, so they are deleted, not kept: there is
    no other basis to keep them. The account, its sign-in methods and the
    record of having read the policy stay. The user is then stopped by the
    consent gate until they consent again or delete the account. One
    transaction: on any error nothing changes.
    """
    from sqlalchemy import inspect as sa_inspect

    from backend.app.models.user import User

    user_id = user.id
    try:
        category_ids = select(Category.id).where(Category.user_id == user_id)
        db.session.execute(
            update(MealItem)
            .where(MealItem.category_id.in_(category_ids))
            .values(category_id=None)
        )
        db.session.execute(delete(Category).where(Category.user_id == user_id))
        for model in _UNCASCADED:
            if model is not TelegramIdentity:
                db.session.execute(delete(model).where(model.user_id == user_id))
        db.session.expire_all()

        user = db.session.get(User, user_id)
        # The same cascades as deleting the account, minus the kept ones.
        for relationship in sa_inspect(User).relationships:
            if not relationship.cascade.delete or relationship.key in _KEPT_RELATIONSHIPS:
                continue
            related = getattr(user, relationship.key)
            if relationship.lazy == "dynamic":
                related = related.all()
            elif not relationship.uselist:
                related = [related] if related is not None else []
            for obj in related:
                db.session.delete(obj)

        fatigue = user.fatigue_state
        user.fatigue_state_id = None
        for column in _USER_HEALTH_COLUMNS:
            setattr(user, column, None)
        user.health_data_consent_at = None
        user.consent_version = None
        db.session.flush()
        if fatigue is not None:
            db.session.delete(fatigue)

        # Any other table that references the user (e.g. activity_events).
        for table in db.metadata.sorted_tables:
            if table.name in _KEPT_TABLES:
                continue
            for column in table.columns:
                if any(fk.column.table.name == "users" for fk in column.foreign_keys):
                    db.session.execute(delete(table).where(column == user_id))

        # An empty profile, as sign-in creates for accounts without one.
        db.session.add(UserProfile(user_id=user_id, training_location="home", onboarding_completed=False))
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
