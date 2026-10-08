from backend.app.extensions import db
from backend.app.factory import create_backend_app
from backend.app.models.recovery.habit import RecoveryHabit
from backend.app.models.recovery.user_habit import UserRecoveryHabit
from backend.app.models.user import User

DEFAULT_RECOVERY_HABITS = (
    "drink_water",
    "sleep_8h",
    "consistent_sleep",
    "balanced_meal",
    "walk_30m",
    "stretching",
)


def run(user_id):
    app = create_backend_app()

    with app.app_context():
        user = db.session.get(User, user_id)

        if not user:
            raise RuntimeError(f"User {user_id} not found")

        habits = RecoveryHabit.query.filter(
            RecoveryHabit.slug.in_(DEFAULT_RECOVERY_HABITS),
            RecoveryHabit.is_active.is_(True),
            RecoveryHabit.is_archived.is_(False),
        ).all()

        existing = UserRecoveryHabit.query.filter_by(user_id=user_id).all()

        existing_by_habit_id = {
            user_habit.habit_id: user_habit for user_habit in existing
        }

        created = 0
        restored = 0

        for habit in habits:
            user_habit = existing_by_habit_id.get(habit.id)

            if user_habit:
                if not user_habit.is_active:
                    user_habit.is_active = True
                    restored += 1
                continue

            db.session.add(
                UserRecoveryHabit(
                    user_id=user_id,
                    habit_id=habit.id,
                    is_active=True,
                )
            )
            created += 1

        db.session.commit()

        print(f"Created {created}, restored {restored}")


if __name__ == "__main__":
    run(1)
