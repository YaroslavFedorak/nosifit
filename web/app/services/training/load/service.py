from .exercise import calculate_exercise_load
from .index import compute_daily_load_index
from .session import calculate_session_load
from web.app.models.training_session import TrainingSession
from datetime import datetime, time


class TrainingLoadService:

    @staticmethod
    def get_daily_load(user_id, target_day):
        start_dt = datetime.combine(target_day, time.min)
        end_dt = datetime.combine(target_day, time.max)

        sessions = (
            TrainingSession.query.filter(
                TrainingSession.user_id == user_id,
                TrainingSession.started_at >= start_dt,
                TrainingSession.started_at <= end_dt,
            )
            .order_by(TrainingSession.started_at.asc())
            .all()
        )

        idx = compute_daily_load_index(user_id, sessions, target_day)
        return idx["load_today"]

    @staticmethod
    def compute_exercise_load(
        session_exercise,
        exercise,
        capacity=None,
    ):
        capacity = capacity or {}

        user_weight = float(capacity.get("weight", 70.0) or 70.0)

        result = calculate_exercise_load(
            exercise=exercise,
            user_weight=user_weight,
            sets=getattr(session_exercise, "sets", 0),
            reps=getattr(session_exercise, "reps", 0),
            additional_weight=getattr(session_exercise, "load", 0),
        )

        return result

    @staticmethod
    def compute_session_load(session, user):
        load = calculate_session_load(session, user)
        return {"internal_load": load, "muscle_loads": session.muscle_loads or {}}

    @staticmethod
    def compute_daily_load_index(
        user,
        sessions,
        target_day=None,
    ):
        return compute_daily_load_index(
            user,
            sessions,
            target_day,
        )
