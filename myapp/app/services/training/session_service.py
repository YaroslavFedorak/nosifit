from datetime import datetime

from myapp.app import db
from myapp.app.models.training_session import (
    TrainingSession,
    SessionExercise,
)
from myapp.app.services.training.load_service import (
    TrainingLoadService,
)
from myapp.app.training_engine.models.exercise import Exercise
from myapp.app.training_engine.models.performance_state import (
    PerformanceState,
)


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

    # LOAD CALCULATION

    @staticmethod
    def _compute_session_load(session):
        user = session.user

        capacity = TrainingLoadService.build_capacity(user)

        total_internal_load = 0.0
        muscle_loads = {}

        exercises = Exercise.query.all()

        exercise_map = {exercise.id: exercise for exercise in exercises}

        for session_exercise in session.exercises:
            exercise = exercise_map.get(session_exercise.exercise_id)

            if not exercise:
                continue

            result = TrainingLoadService.compute_exercise_load(
                session_exercise,
                exercise,
                capacity,
            )

            internal_load = result["internal_load"]

            total_internal_load += internal_load

            TrainingLoadService.compute_muscle_load(
                exercise,
                internal_load,
                muscle_loads,
            )

        # Avoid floating-point noise in JSON/database.
        muscle_loads = {
            muscle: round(value, 2)
            for muscle, value in muscle_loads.items()
            if value > 0
        }

        session.internal_load = round(
            total_internal_load,
            2,
        )

        session.muscle_loads = muscle_loads

        return session.internal_load

    @staticmethod
    def update_training_load_from_session(
        session,
        user,
    ):
        total_load = TrainingSessionService._compute_session_load(session)

        performance = user.performance_states.order_by(
            PerformanceState.created_at.desc()
        ).first()

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

    # FINISH SESSION

    @staticmethod
    def finish_session(
        session,
        fatigue_after=None,
    ):
        session.status = "finished"
        session.finished_at = datetime.utcnow()
        session.fatigue_after = fatigue_after

        rpes = [
            exercise.rpe for exercise in session.exercises if exercise.rpe is not None
        ]

        if rpes:
            session.rpe_avg = sum(rpes) / len(rpes)
        else:
            session.rpe_avg = None

        # Calculate internal_load + muscle_loads
        # before committing the finished session.
        TrainingSessionService._compute_session_load(session)

        db.session.commit()

        # Update user's cumulative training load.
        TrainingSessionService.update_training_load_from_session(
            session,
            session.user,
        )

        return session
