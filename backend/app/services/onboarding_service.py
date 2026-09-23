from backend.app.extensions import db
from backend.app.models.user_profile import UserProfile
from backend.app.models.user_goals import UserTrainingGoals
from backend.app.models.user_injury import UserInjury
from backend.app.models.recovery.habit import RecoveryHabit
from backend.app.models.recovery.user_habit import UserRecoveryHabit


class OnboardingService:

    DEFAULT_RECOVERY_HABITS = (
        "drink_water",
        "sleep_8h",
        "consistent_sleep",
        "balanced_meal",
        "walk_30m",
        "stretching",
    )

    @staticmethod
    def save_profile(
        user,
        training_location,
        wants_nutrition,
        wants_recovery,
    ):
        profile = UserProfile.query.filter_by(user_id=user.id).first()

        if not profile:
            profile = UserProfile(user_id=user.id)
            db.session.add(profile)

        profile.training_location = training_location
        profile.wants_nutrition = wants_nutrition
        profile.wants_recovery = wants_recovery

        db.session.commit()

        return profile

    @staticmethod
    def save_goals(
        user,
        primary_goal,
        focus_upper,
        focus_lower,
        focus_core,
    ):
        goals = UserTrainingGoals.query.filter_by(user_id=user.id).first()

        if not goals:
            goals = UserTrainingGoals(user_id=user.id)
            db.session.add(goals)

        goals.primary_goal = primary_goal
        goals.focus_upper = focus_upper
        goals.focus_lower = focus_lower
        goals.focus_core = focus_core

        db.session.commit()

        return goals

    @staticmethod
    def save_injuries(user, injury_ids):
        UserInjury.query.filter_by(user_id=user.id).delete()

        for injury_id in injury_ids:
            db.session.add(
                UserInjury(
                    user_id=user.id,
                    injury_id=injury_id,
                )
            )

        db.session.commit()

    @staticmethod
    def create_default_recovery_habits(user):
        profile = UserProfile.query.filter_by(user_id=user.id).first()

        if not profile or not profile.wants_recovery:
            return []

        habits = RecoveryHabit.query.filter(
            RecoveryHabit.slug.in_(OnboardingService.DEFAULT_RECOVERY_HABITS),
            RecoveryHabit.is_active.is_(True),
            RecoveryHabit.is_archived.is_(False),
        ).all()

        existing = UserRecoveryHabit.query.filter_by(user_id=user.id).all()

        existing_by_habit_id = {
            user_habit.habit_id: user_habit for user_habit in existing
        }

        created = []

        for habit in habits:
            user_habit = existing_by_habit_id.get(habit.id)

            if user_habit:
                if not user_habit.is_active:
                    user_habit.is_active = True
                continue

            user_habit = UserRecoveryHabit(
                user_id=user.id,
                habit_id=habit.id,
                is_active=True,
            )

            db.session.add(user_habit)
            created.append(user_habit)

        return created

    @staticmethod
    def complete_onboarding(user):
        profile = UserProfile.query.filter_by(user_id=user.id).first()

        if not profile:
            profile = UserProfile(user_id=user.id)
            db.session.add(profile)

        profile.onboarding_completed = True

        OnboardingService.create_default_recovery_habits(user)

        db.session.commit()

        return profile
