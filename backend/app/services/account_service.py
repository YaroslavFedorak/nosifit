"""Deleting an account together with all personal data it owns."""

from sqlalchemy import delete, select, update

from backend.app.extensions import db
from backend.app.models.nutrition.category import Category
from backend.app.models.nutrition.meal_item import MealItem
from backend.app.models.nutrition.saved_meal import SavedMeal
from backend.app.models.nutrition.user_goals import UserGoals
from backend.app.models.nutrition.user_water import UserWater
from backend.app.models.nutrition.user_weight import UserWeight
from backend.app.models.recovery_plan import RecoveryPlan
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
    SavedMeal,
    RecoveryPlan,
    UserInjury,
    UserTrainingGoals,
    UserProfile,
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
