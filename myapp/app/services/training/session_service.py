from datetime import datetime

from myapp.app import db
from myapp.app.models.training_session import (
    SessionExercise,
    TrainingSession,
)
from myapp.app.services.training.load import (
    TrainingLoadService,
    calculate_session_load,
)
from myapp.app.training_engine.models.performance_state import PerformanceState


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

        if "sets_done" in data:
            session_exercise.sets_done = data["sets_done"]

        if "reps_done" in data:
            session_exercise.reps_done = data["reps_done"]

        if "load_done" in data:
            session_exercise.load_done = data["load_done"]

        if "rpe" in data:
            session_exercise.rpe = data["rpe"]

        db.session.commit()
        return session_exercise

    @staticmethod
    def _compute_muscle_loads(session):
        loads = {}
        for exercise in session.exercises:
            if exercise.load_done and exercise.rpe:
                loads[str(exercise.exercise_id)] = float(exercise.load_done) * float(
                    exercise.rpe
                )
        return loads

    @staticmethod
    def _compute_session_load(session, user):
        internal_load = calculate_session_load(session, user)
        session.internal_load = internal_load
        session.muscle_loads = TrainingSessionService._compute_muscle_loads(session)
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
