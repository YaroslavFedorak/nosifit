"""Database access for the training model: a fixed number of queries per call.

Rows are converted into the plain records of ``records.py``; nothing below
this module touches the ORM.
"""

from datetime import date, datetime
from types import MappingProxyType
from typing import Dict, Iterable, List, Mapping, Optional

from sqlalchemy import func
from sqlalchemy.orm import selectinload

from backend.app.extensions import db
from backend.app.models.recovery.sleep_entry import SleepEntry
from backend.app.models.training_session import TrainingSession
from backend.app.models.user_equipment import UserEquipment
from backend.app.models.user_goals import UserTrainingGoals
from backend.app.models.user_profile import UserProfile
from backend.app.training.exercises.prescription import performed_values
from backend.app.training.models.equipment import TEEquipment
from backend.app.training.models.exercise import Exercise
from backend.app.utils import clock

from .context import TrainingContext, build_context
from .records import ExerciseInfo, LoggedEntry, SleepNight


_catalog_cache = (None, MappingProxyType({}))


def load_catalog() -> Mapping[str, ExerciseInfo]:
    """Every exercise as a plain record, rebuilt only when the catalog changes.

    The catalog changes only when it is seeded, and one saved workout or one
    dashboard needs it several times. A count + last update check notices a
    reseed; the records are immutable, so all requests can share them.
    """
    global _catalog_cache
    key = tuple(db.session.query(func.count(Exercise.id), func.max(Exercise.updated_at)).one())
    if key != _catalog_cache[0]:
        _catalog_cache = (
            key,
            MappingProxyType(
                {row.id: ExerciseInfo.from_mapping(row.to_dict()) for row in Exercise.query.all()}
            ),
        )
    return _catalog_cache[1]


def load_sessions(user_id: int, since: datetime, until: Optional[datetime] = None) -> List[TrainingSession]:
    query = (
        TrainingSession.query.options(selectinload(TrainingSession.exercises))
        .filter(TrainingSession.user_id == user_id, TrainingSession.started_at >= since)
    )
    if until is not None:
        query = query.filter(TrainingSession.started_at <= until)
    return query.order_by(TrainingSession.started_at.asc(), TrainingSession.id.asc()).all()


def session_time(session) -> Optional[datetime]:
    return getattr(session, "finished_at", None) or getattr(session, "started_at", None)


def entries_from_sessions(sessions: Iterable, catalog: Mapping[str, ExerciseInfo]) -> List[LoggedEntry]:
    entries = []
    for session in sessions:
        performed_at = session_time(session)
        if performed_at is None:
            continue
        for session_exercise in getattr(session, "exercises", None) or []:
            exercise = catalog.get(session_exercise.exercise_id)
            if exercise is None:
                continue
            values = performed_values(session_exercise, exercise)
            entries.append(
                LoggedEntry(
                    session_id=getattr(session, "id", None),
                    exercise_id=session_exercise.exercise_id,
                    performed_at=performed_at,
                    sets=values["sets"],
                    reps=values["reps"] or None,
                    duration_sec=values["duration_sec"] or None,
                    load_kg=values["load"] or 0.0,
                    rpe=getattr(session_exercise, "rpe", None),
                )
            )
    return entries


def load_sleep(user_id: int, since: date) -> List[SleepNight]:
    rows = SleepEntry.query.filter(
        SleepEntry.user_id == user_id,
        SleepEntry.sleep_end >= datetime.combine(since, datetime.min.time()),
    ).all()
    return [
        SleepNight(night=clock.to_local_date(row.sleep_end), minutes=int(row.duration_minutes or 0))
        for row in rows
    ]


def load_equipment_slugs(user_id: int) -> List[str]:
    rows = (
        TEEquipment.query.join(UserEquipment, UserEquipment.equipment_id == TEEquipment.id)
        .filter(UserEquipment.user_id == user_id, UserEquipment.available.isnot(False))
        .all()
    )
    return sorted(row.slug for row in rows)


def load_context(user) -> TrainingContext:
    user_id = getattr(user, "id", None)
    profile = UserProfile.query.filter_by(user_id=user_id).first() if user_id else None
    goals = UserTrainingGoals.query.filter_by(user_id=user_id).first() if user_id else None
    equipment = load_equipment_slugs(user_id) if user_id else []
    return build_context(user, profile, goals, equipment)
