"""Reads of the exercise, muscle and equipment catalogs."""

from types import SimpleNamespace

from sqlalchemy import func

from backend.app.extensions import db
from backend.app.models.training_session import SessionExercise, TrainingSession
from backend.app.training.models.equipment import TEEquipment
from backend.app.training.models.exercise import Exercise
from backend.app.training.models.muscle import Muscle


def list_muscles():
    return Muscle.query.order_by(Muscle.name)


def list_equipment():
    return TEEquipment.query.order_by(TEEquipment.name)


def find_exercises(*, muscle=None, equipment=None, name=None, page=1, per_page=50):
    """One page of exercises by name, optionally filtered."""
    q = Exercise.query

    if muscle:
        q = q.filter(
            Exercise.muscles_primary.contains([muscle])
            | Exercise.muscles_secondary.contains([muscle])
        )

    if equipment:
        q = q.filter(Exercise.equipment.contains([equipment]))

    if name:
        q = q.filter(Exercise.name.ilike(f"%{name}%"))

    return q.order_by(Exercise.name).paginate(page=page, per_page=per_page, error_out=False)


def exercise_by_id(exercise_id):
    return Exercise.query.get(exercise_id)


def exercises_by_id(exercise_ids):
    """id -> exercise for the given ids that exist."""
    if not exercise_ids:
        return {}
    return {
        exercise.id: exercise
        for exercise in Exercise.query.filter(Exercise.id.in_(list(exercise_ids)))
    }


def exercise_ids_done_by(user_id):
    """Ids of every exercise the user has logged at least once."""
    return {
        exercise_id
        for (exercise_id,) in db.session.query(SessionExercise.exercise_id)
        .join(TrainingSession, SessionExercise.session_id == TrainingSession.id)
        .filter(TrainingSession.user_id == user_id)
        .distinct()
    }


_catalog_cache = {"key": None, "rows": []}


def catalog_snapshot():
    """The exercise catalog as plain objects, rebuilt only when it changes.

    The catalog changes only when it is seeded; reading every exercise on
    each search made the bot slow. A count + last update check is enough to
    notice a reseed.
    """
    key = tuple(
        db.session.query(func.count(Exercise.id), func.max(Exercise.updated_at)).one()
    )
    if key != _catalog_cache["key"]:
        _catalog_cache["rows"] = [
            SimpleNamespace(
                id=row.id,
                slug=row.slug,
                name=row.name,
                measurement_type=row.measurement_type,
                load_type=row.load_type,
                max_additional_load_kg=row.max_additional_load_kg,
                prescription=row.prescription,
            )
            for row in Exercise.query.all()
        ]
        _catalog_cache["key"] = key
    return _catalog_cache["rows"]
