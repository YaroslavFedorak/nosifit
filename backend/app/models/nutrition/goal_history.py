from datetime import datetime

from sqlalchemy import event, func, inspect, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from backend.app.extensions import db
from backend.app.utils import clock


class NutritionGoalHistory(db.Model):
    """The nutrition targets a user had from ``effective_from`` on.

    A row is written when the targets change (see ``record_goal_change``), so
    a past day can be compared with the targets of that day instead of
    today's. Days before the first row have no stored targets and are never
    reconstructed (see ``goal_history_service``).
    """

    __tablename__ = "nutrition_goal_history"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )

    effective_from = db.Column(db.Date, nullable=False)

    calories = db.Column(db.Integer, nullable=False)
    protein = db.Column(db.Float, nullable=False)
    fat = db.Column(db.Float, nullable=False)
    carbs = db.Column(db.Float, nullable=False)
    fiber = db.Column(db.Float, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint(
            "user_id", "effective_from", name="uq_nutrition_goal_history_day"
        ),
    )

    def __repr__(self):
        return (
            f"<NutritionGoalHistory user_id={self.user_id} "
            f"from={self.effective_from} calories={self.calories}>"
        )


# Profile columns the targets are calculated from.
_GOAL_INPUTS = ("weight", "height", "age", "gender", "activity", "goal")


def _same(row, goals):
    return (
        row.calories == goals["calories"]
        and abs(row.protein - goals["protein"]) < 1e-6
        and abs(row.fat - goals["fat"]) < 1e-6
        and abs(row.carbs - goals["carbs"]) < 1e-6
    )


# Namespace of the advisory lock that serialises one user's profile writes.
_LOCK_NAMESPACE = 7021


def lock_profile_writes(session, user_id):
    """Take the user's profile-write lock (held until the transaction ends).

    Locking protocol - every transaction that writes a user's profile row takes
    this lock *before* its first UPDATE/INSERT of that row (this function is
    called from the flush hook below, ahead of the statements it flushes):

    1. The lock is always acquired before the row lock, never after. Two
       writers therefore queue on the advisory lock and can no longer wait for
       each other's row lock while holding the advisory one (no deadlock
       between the two).
    2. Whoever gets the lock after another writer sees that writer's committed
       result (PostgreSQL READ COMMITTED, the project's isolation level: each
       statement reads the latest committed data), which is what makes the
       fresh read in :func:`current_goal_inputs` correct.
    """
    session.execute(select(func.pg_advisory_xact_lock(_LOCK_NAMESPACE, user_id)))


def current_goal_inputs(session, profile):
    """The profile values the targets are calculated from, as of now.

    The in-memory profile can be stale: it was loaded before another
    transaction committed a change to a *different* column. Saving writes only
    the columns this transaction changed, so the row that results is the
    committed row plus those changes - and that, not the stale object, is
    what the targets must be calculated from. Call it after
    :func:`lock_profile_writes`, when no other writer can still be in flight.
    """
    state = inspect(profile)
    stored = session.execute(
        select(*(getattr(type(profile), name) for name in _GOAL_INPUTS)).where(
            type(profile).user_id == profile.user_id
        )
    ).first()
    values = {}
    for index, name in enumerate(_GOAL_INPUTS):
        changed = state.attrs[name].history.has_changes()
        if changed or stored is None:
            values[name] = getattr(profile, name)      # this transaction's value
        else:
            values[name] = stored[index]                # the committed value
    return values


def record_goal_change(session, profile):
    """Store the targets ``profile`` now gives, when they differ from the last.

    Runs inside the flush that saves the profile, so every place that edits
    a profile (the profile form, onboarding, a new weight) is covered without
    each one calling it, and reading targets never writes. A profile that
    does not give targets (incomplete) stores nothing. The caller holds the
    user's profile-write lock (see :func:`lock_profile_writes`).

    The day's row is written with a single atomic ``INSERT ... ON CONFLICT
    (user_id, effective_from) DO UPDATE``, so two saves can never collide on
    the unique key, and the last one to commit wins.
    """
    from types import SimpleNamespace

    from backend.app.models.nutrition.user_goals import UserGoals
    from backend.app.services.nutrition.calories_service import (
        calculate_nutrition_goals,
    )

    with session.no_autoflush:
        inputs = current_goal_inputs(session, profile)
        goals = calculate_nutrition_goals(SimpleNamespace(profile=SimpleNamespace(**inputs)))
        if goals is None:
            return

        stored = session.execute(
            select(UserGoals.fiber_goal).where(UserGoals.user_id == profile.user_id)
        ).scalar()
        fiber = stored if stored else 30.0
        today = clock.today()
        # Columns, not the entity: nothing stale can stay in the session.
        latest = session.execute(
            select(
                NutritionGoalHistory.calories,
                NutritionGoalHistory.protein,
                NutritionGoalHistory.fat,
                NutritionGoalHistory.carbs,
            )
            .where(NutritionGoalHistory.user_id == profile.user_id)
            .order_by(NutritionGoalHistory.effective_from.desc())
            .limit(1)
        ).first()

        if latest is not None and _same(latest, goals):
            return

        values = {
            "calories": goals["calories"],
            "protein": goals["protein"],
            "fat": goals["fat"],
            "carbs": goals["carbs"],
            "fiber": fiber,
        }
        session.execute(
            pg_insert(NutritionGoalHistory.__table__)
            .values(
                user_id=profile.user_id,
                effective_from=today,
                created_at=datetime.utcnow(),
                **values,
            )
            .on_conflict_do_update(
                index_elements=["user_id", "effective_from"],
                set_=values,
            )
        )


def _on_before_flush(session, flush_context, instances):
    from backend.app.models.user_profile import UserProfile

    candidates = [
        obj for obj in list(session.new) + list(session.dirty)
        if isinstance(obj, UserProfile)
    ]
    for profile in candidates:
        if profile.user_id is None:
            continue
        is_new = profile in session.new
        state = inspect(profile)
        columns = [attr.key for attr in state.mapper.column_attrs]
        if not is_new and not any(state.attrs[name].history.has_changes() for name in columns):
            continue
        # Any write of the profile row - not only of the columns the targets
        # depend on - queues behind the lock first (protocol: lock, then row).
        with session.no_autoflush:
            lock_profile_writes(session, profile.user_id)
        if is_new or any(state.attrs[name].history.has_changes() for name in _GOAL_INPUTS):
            record_goal_change(session, profile)


event.listen(Session, "before_flush", _on_before_flush)
