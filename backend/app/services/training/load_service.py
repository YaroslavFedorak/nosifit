from types import SimpleNamespace

from backend.app.services.training.load.service import TrainingLoadService


def _compute_exercise_load(
    exercise, sets, reps, load, user_weight=70.0, duration_sec=None
):
    session_exercise = SimpleNamespace(
        sets=sets,
        reps=reps,
        duration_sec=duration_sec,
        load=load,
    )

    capacity = {
        "weight": float(user_weight or 70.0),
    }

    result = TrainingLoadService.compute_exercise_load(
        session_exercise=session_exercise,
        exercise=exercise,
        capacity=capacity,
    )

    return result.get("internal_load", 0.0)

