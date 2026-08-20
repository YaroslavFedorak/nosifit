from datetime import date, datetime

from myapp.app import db
from myapp.app.models.training_session import TrainingSession
from myapp.app.training_engine.models.exercise import Exercise
from myapp.app.services.training.session_service import TrainingSessionService

from .analyzer import TrainingDashboardAnalyzer
from .dto import (
    exercise_to_dict,
    session_exercise_to_dict,
    training_session_to_dict,
)


class TrainingDashboardService:

    @staticmethod
    def get_today(user_id):
        start = datetime.combine(date.today(), datetime.min.time())
        end = datetime.combine(date.today(), datetime.max.time())

        session = (
            TrainingSession.query.filter(
                TrainingSession.user_id == user_id,
                TrainingSession.started_at >= start,
                TrainingSession.started_at <= end,
            )
            .order_by(TrainingSession.id.desc())
            .first()
        )

        if not session:
            return {
                "session": None,
                "summary": TrainingDashboardAnalyzer.build_widget(None),
            }

        return {
            "session": training_session_to_dict(session),
            "summary": TrainingDashboardAnalyzer.build_widget(session),
        }

    @staticmethod
    def get_session(user_id, session_id):
        session = TrainingSession.query.filter_by(
            id=session_id,
            user_id=user_id,
        ).first()

        if not session:
            return None

        return {
            "session": training_session_to_dict(session),
            "summary": TrainingDashboardAnalyzer.build_widget(session),
        }

    @staticmethod
    def get_exercises(
        search=None,
        movement_pattern=None,
        difficulty=None,
    ):
        query = Exercise.query

        if search:
            query = query.filter(Exercise.name.ilike(f"%{search.strip()}%"))

        if movement_pattern:
            query = query.filter(Exercise.movement_pattern == movement_pattern)

        if difficulty:
            try:
                query = query.filter(Exercise.difficulty <= int(difficulty))
            except (TypeError, ValueError):
                pass

        exercises = (
            query.order_by(
                Exercise.difficulty.asc(),
                Exercise.name.asc(),
            )
            .limit(100)
            .all()
        )

        return [exercise_to_dict(exercise) for exercise in exercises]

    @staticmethod
    def start(user_id, fatigue_before=None):
        from myapp.app.models.user import User

        user = User.query.get(user_id)

        if not user:
            return None

        existing = (
            TrainingSession.query.filter_by(
                user_id=user_id,
                status="active",
            )
            .order_by(TrainingSession.id.desc())
            .first()
        )

        if existing:
            return training_session_to_dict(existing)

        session = TrainingSessionService.start_session(
            user,
            fatigue_before=fatigue_before,
        )

        return training_session_to_dict(session)

    @staticmethod
    def add_exercise(user_id, session_id, exercise_id):
        session = TrainingSession.query.filter_by(
            id=session_id,
            user_id=user_id,
        ).first()

        if not session or session.status != "active":
            return None

        exercise = Exercise.query.get(exercise_id)

        if not exercise:
            return None

        session_exercise = TrainingSessionService.add_exercise(
            session,
            exercise_id,
        )

        return session_exercise_to_dict(
            session_exercise,
            exercise,
        )

    @staticmethod
    def update_exercise(
        user_id,
        session_id,
        exercise_id,
        data,
    ):
        session = TrainingSession.query.filter_by(
            id=session_id,
            user_id=user_id,
        ).first()

        if not session or session.status != "active":
            return None

        session_exercise = TrainingSessionService.update_exercise(
            session,
            exercise_id,
            data,
        )

        if not session_exercise:
            return None

        exercise = Exercise.query.get(exercise_id)

        return session_exercise_to_dict(
            session_exercise,
            exercise,
        )

    @staticmethod
    def finish(
        user_id,
        session_id,
        fatigue_after=None,
    ):
        session = TrainingSession.query.filter_by(
            id=session_id,
            user_id=user_id,
        ).first()

        if not session:
            return None

        if session.status == "finished":
            return training_session_to_dict(session)

        session = TrainingSessionService.finish_session(
            session,
            fatigue_after=fatigue_after,
        )

        db.session.refresh(session)

        return training_session_to_dict(session)
