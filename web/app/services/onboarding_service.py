from web.app import db
from web.app.models.user_profile import UserProfile
from web.app.models.user_goals import UserTrainingGoals
from web.app.models.user_injury import UserInjury


class OnboardingService:

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
    def complete_onboarding(user):
        profile = UserProfile.query.filter_by(user_id=user.id).first()

        if not profile:
            profile = UserProfile(user_id=user.id)
            db.session.add(profile)

        profile.onboarding_completed = True

        db.session.commit()

        return profile
