from datetime import datetime

from myapp.app import db
from myapp.app.models.training_session import TrainingSession, SessionExercise
from myapp.app.services.training.load_service import TrainingLoadService
from myapp.app.training_engine.models.exercise import Exercise
from myapp.app.training_engine.models.performance_state import PerformanceState


class TrainingSessionService:
    @staticmethod
    def start_session(user, fatigue_before=None):
        session = TrainingSession(
            user_id=user.id,
            fatigue_before=fatigue_before,
            status="active",
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

        se = SessionExercise(
            session_id=session.id,
            exercise_id=exercise_id,
            sets_planned=0,
        )
        db.session.add(se)
        db.session.commit()
        return se

    @staticmethod
    def update_exercise(session, exercise_id, data):
        se = SessionExercise.query.filter_by(
            session_id=session.id,
            exercise_id=exercise_id,
        ).first()

        if not se:
            se = TrainingSessionService.add_exercise(session, exercise_id)

        se.sets_done = data.get("sets_done", se.sets_done)
        se.reps_done = data.get("reps_done", se.reps_done)
        se.load_done = data.get("load_done", se.load_done)
        se.rpe = data.get("rpe", se.rpe)

        db.session.commit()
        return se

    @staticmethod
    def _compute_session_load(session):
        user = session.user
        capacity = TrainingLoadService.build_capacity(user)

        total_internal = 0.0
        muscle_loads = {}

        for se in session.exercises:
            ex = Exercise.query.get(se.exercise_id)
            if not ex:
                continue

            load_data = TrainingLoadService.compute_exercise_load(se, ex, capacity)
            internal = load_data["internal_load"]
            total_internal += internal

            TrainingLoadService.compute_muscle_load(ex, internal, muscle_loads)

        session.internal_load = total_internal
        session.muscle_loads = muscle_loads
        db.session.commit()
        return total_internal

    @staticmethod
    def update_training_load_from_session(session, user):
        total_load = TrainingSessionService._compute_session_load(session)

        last_perf = user.performance_states.order_by(
            PerformanceState.created_at.desc()
        ).first()

        if not last_perf:
            ps = PerformanceState(
                user_id=user.id,
                training_load=total_load,
                weight=user.weight,
            )
            db.session.add(ps)
            db.session.commit()
            return

        last_perf.training_load = (last_perf.training_load or 0) + total_load
        db.session.commit()

    @staticmethod
    def finish_session(session, fatigue_after=None):
        session.status = "finished"
        session.finished_at = datetime.utcnow()
        session.fatigue_after = fatigue_after

        rpes = [se.rpe for se in session.exercises if se.rpe is not None]
        session.rpe_avg = sum(rpes) / len(rpes) if rpes else None

        db.session.commit()
        TrainingSessionService.update_training_load_from_session(session, session.user)
        return session
