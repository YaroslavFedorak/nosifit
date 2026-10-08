from datetime import datetime

from backend.app.extensions import db
from backend.app.models.training_session import (
    SessionExercise,
    TrainingSession,
)
from backend.app.services.training.load import calculate_session_load
from backend.app.services.training.model import TrainingModelService
from backend.app.training.exercises.prescription import session_update_fields
from backend.app.training.models.exercise import Exercise
from backend.app.training.models.performance_state import PerformanceState


class TrainingSessionService:

    @staticmethod
    def start_session(user, fatigue_before=None):
        session = TrainingSession(
            user_id=user.id,
            fatigue_before=fatigue_before,
            status="active",
            started_at=datetime.utcnow(),
        )

        db.session.add(session)
        db.session.commit()
        return session

    @staticmethod
    def add_exercise(session, exercise_id):
        existing = SessionExercise.query.filter_by(
            session_id=session.id,
            exercise_id=exercise_id,
        ).first()

        if existing:
            return existing

        session_exercise = SessionExercise(
            session_id=session.id,
            exercise_id=exercise_id,
            sets_planned=0,
            sets_done=0,
        )

        db.session.add(session_exercise)
        db.session.commit()
        return session_exercise

    @staticmethod
    def update_exercise(session, exercise_id, data):
        session_exercise = SessionExercise.query.filter_by(
            session_id=session.id,
            exercise_id=exercise_id,
        ).first()

        if not session_exercise:
            session_exercise = TrainingSessionService.add_exercise(
                session,
                exercise_id,
            )

        exercise = Exercise.query.get(exercise_id)

        for field, value in session_update_fields(exercise, data).items():
            setattr(session_exercise, field, value)

        db.session.commit()
        return session_exercise

    @staticmethod
    def _compute_session_load(session, user):
        # internal_load: legacy multiplier-based number, still read by the
        # dashboard session score; removed once that consumer moves.
        internal_load = calculate_session_load(session, user)
        session.internal_load = internal_load
        # The muscle_loads column now stores effective sets per muscle (v2
        # model). It used to hold exercise ids by mistake.
        session.muscle_loads = TrainingModelService.session_summary(session)["muscle_sets"]
        return internal_load

    @staticmethod
    def update_training_load_from_session(session, user):
        total_load = TrainingSessionService._compute_session_load(session, user)

        performance = (
            PerformanceState.query.filter_by(user_id=user.id)
            .order_by(PerformanceState.created_at.desc())
            .first()
        )

        if not performance:
            performance = PerformanceState(
                user_id=user.id,
                training_load=total_load,
                weight=user.weight,
            )
            db.session.add(performance)
        else:
            performance.training_load = (performance.training_load or 0) + total_load

        db.session.commit()

    @staticmethod
    def finish_session(session, fatigue_after=None):
        session.status = "finished"
        session.finished_at = datetime.utcnow()
        session.fatigue_after = fatigue_after

        rpes = [ex.rpe for ex in session.exercises if ex.rpe is not None]
        session.rpe_avg = sum(rpes) / len(rpes) if rpes else None

        TrainingSessionService._compute_session_load(session, session.user)

        db.session.commit()

        TrainingSessionService.update_training_load_from_session(
            session,
            session.user,
        )

        return session

