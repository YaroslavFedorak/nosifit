from .exercise import calculate_exercise_load
from .index import compute_daily_load_index
from .session import calculate_session_load


class TrainingLoadService:

    @staticmethod
    def get_daily_load(user, sessions, target_day):
        idx = compute_daily_load_index(user, sessions, target_day)
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
