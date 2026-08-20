def exercise_to_dict(exercise):
    return {
        "id": exercise.id,
        "name": exercise.name,
        "slug": exercise.slug,
        "difficulty": exercise.difficulty,
        "movement_pattern": exercise.movement_pattern,
        "equipment": exercise.equipment or [],
    }


def session_exercise_to_dict(
    session_exercise,
    exercise=None,
):
    return {
        "id": session_exercise.id,
        "exercise_id": session_exercise.exercise_id,
        "exercise": exercise.name if exercise else None,
        "sets": (session_exercise.sets_done or session_exercise.sets_planned or 0),
        "reps": (session_exercise.reps_done or session_exercise.reps_planned or ""),
        "load": session_exercise.load_done,
        "rpe": session_exercise.rpe,
    }


def training_session_to_dict(session):
    exercises = []

    for session_exercise in session.exercises:
        exercise = getattr(
            session_exercise,
            "exercise",
            None,
        )

        exercises.append(
            session_exercise_to_dict(
                session_exercise,
                exercise,
            )
        )

    return {
        "id": session.id,
        "status": session.status,
        "started_at": (session.started_at.isoformat() if session.started_at else None),
        "finished_at": (
            session.finished_at.isoformat() if session.finished_at else None
        ),
        "fatigue_before": session.fatigue_before,
        "fatigue_after": session.fatigue_after,
        "duration": _duration_minutes(session),
        "exercise_count": len(exercises),
        "rpe_avg": session.rpe_avg,
        "internal_load": session.internal_load or 0,
        "exercises": exercises,
    }


def training_summary_to_dict(
    score=None,
    completed=False,
    duration=0,
    exercise_count=0,
    internal_load=0,
):
    return {
        "score": score,
        "completed": bool(completed),
        "duration": duration or 0,
        "exercise_count": exercise_count or 0,
        "internal_load": internal_load or 0,
    }


def _duration_minutes(session):
    if not session.started_at:
        return 0

    from datetime import datetime

    end = session.finished_at or datetime.utcnow()

    seconds = (end - session.started_at).total_seconds()

    if seconds <= 0:
        return 0

    return int(round(seconds / 60))
