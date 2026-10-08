from backend.app.training.exercises.prescription import (
    is_duration_exercise,
    is_per_side,
    measurement_type_of,
)


def exercise_to_dict(exercise):
    return {
        "id": exercise.id,
        "name": exercise.name,
        "slug": exercise.slug,
        "difficulty": exercise.difficulty,
        "movement_pattern": exercise.movement_pattern,
        "equipment": exercise.equipment or [],
        "measurement_type": measurement_type_of(exercise),
        "prescription": exercise.prescription,
    }


def session_exercise_to_dict(
    session_exercise,
    exercise=None,
):
    duration = exercise is not None and is_duration_exercise(exercise)

    return {
        "id": session_exercise.id,
        "exercise_id": session_exercise.exercise_id,
        "exercise": (exercise.name if exercise else None),
        "measurement_type": measurement_type_of(exercise),
        "sets": (
            session_exercise.sets_done
            if session_exercise.sets_done is not None
            else session_exercise.sets_planned or 0
        ),
        "reps": (
            None
            if duration
            else (
                session_exercise.reps_done
                if session_exercise.reps_done is not None
                else session_exercise.reps_planned or ""
            )
        ),
        "duration_sec": (
            (
                session_exercise.duration_sec_done
                if session_exercise.duration_sec_done is not None
                else session_exercise.duration_sec_planned
            )
            if duration
            else None
        ),
        "per_side": exercise is not None and is_per_side(exercise),
        "load": session_exercise.load_done,
        "rpe": session_exercise.rpe,
    }


def training_session_to_dict(session):
    from backend.app.training.models.exercise import Exercise

    exercise_ids = {
        session_exercise.exercise_id for session_exercise in session.exercises
    }

    exercises = (
        Exercise.query.filter(Exercise.id.in_(exercise_ids)).all()
        if exercise_ids
        else []
    )

    exercise_map = {exercise.id: exercise for exercise in exercises}

    session_exercises = []

    for session_exercise in session.exercises:
        exercise = exercise_map.get(session_exercise.exercise_id)

        session_exercises.append(
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
        "exercise_count": len(session_exercises),
        "rpe_avg": session.rpe_avg,
        "internal_load": session.internal_load or 0,
        "muscle_loads": session.muscle_loads or {},
        "exercises": session_exercises,
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

