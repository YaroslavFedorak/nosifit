"""A user's training plans. Only one plan is active at a time."""

from datetime import timedelta

from sqlalchemy.exc import IntegrityError

from backend.app.extensions import db
from backend.app.models.training_session import SessionExercise, TrainingSession
from backend.app.services.training import catalog_service, plan_days
from backend.app.services.training.session_service import TrainingSessionService
from backend.app.training.exercises.prescription import session_update_fields
from backend.app.training.models.training_plan import TrainingPlan


class PlanConflict(Exception):
    """A request that is valid but cannot be applied to the plan's state."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def list_plans(user_id):
    return TrainingPlan.query.filter_by(user_id=user_id)


def count_plans(user_id) -> int:
    return TrainingPlan.query.filter_by(user_id=user_id).count()


def active_plan(user_id):
    return (
        TrainingPlan.query.filter_by(user_id=user_id, is_active=True)
        .order_by(TrainingPlan.id.desc())
        .first()
    )


def plan_for_user(plan_id, user_id):
    """The plan if it belongs to the user, else None."""
    return TrainingPlan.query.filter_by(id=plan_id, user_id=user_id).first()


def _deactivate_plans(user_id) -> None:
    TrainingPlan.query.filter_by(user_id=user_id, is_active=True).update({"is_active": False})


def create_plan(user_id, *, name, days, is_active):
    plan = TrainingPlan(user_id=user_id, name=name, is_active=is_active, days=days)

    if plan.is_active:
        _deactivate_plans(user_id)

    db.session.add(plan)
    db.session.commit()
    return plan


def save_plan(plan, *, name, days, make_active):
    plan.name = name
    plan.days = days

    if make_active:
        _deactivate_plans(plan.user_id)
        plan.is_active = True
    else:
        plan.is_active = False

    db.session.commit()
    return plan


def delete_plan(plan) -> None:
    db.session.delete(plan)
    db.session.commit()


def week_start(today):
    """Monday of the week ``today`` belongs to."""
    return today - timedelta(days=today.weekday())


def day_exercises(plan, day_key):
    day = (plan.days or {}).get(day_key)
    items = day.get("exercises") if isinstance(day, dict) else day
    return items if isinstance(items, list) else []


def completed_sessions(plan, start):
    """date -> session completing a day of ``plan`` in the week from ``start``."""
    rows = TrainingSession.query.filter(
        TrainingSession.plan_id == plan.id,
        TrainingSession.plan_date >= start,
        TrainingSession.plan_date <= start + timedelta(days=6),
    )
    return {row.plan_date: row for row in rows}


def week_status(plan, today):
    """The seven days of ``plan`` for the current week with completion state.

    An empty or missing day is a rest day. Completion comes from the sessions
    linked to the plan, so editing the plan never changes it.
    """
    start = week_start(today)
    done = completed_sessions(plan, start)
    days = []
    for index, key in enumerate(plan_days.WEEKDAYS):
        date = start + timedelta(days=index)
        day = (plan.days or {}).get(key)
        meta = day if isinstance(day, dict) else {}
        count = len(day_exercises(plan, key))
        days.append(
            {
                "key": key,
                "date": date.isoformat(),
                "location": meta.get("location"),
                "equipment": meta.get("equipment"),
                "exercises": count,
                "rest": count == 0,
                "completed": date in done,
                "session_id": done[date].id if date in done else None,
                "is_today": date == today,
            }
        )
    return {"plan_id": plan.id, "week_start": start.isoformat(), "today": today.isoformat(), "days": days}


def complete_day(plan, day_key, day_date, performed_at):
    """Record the planned workout of ``day_key`` as done on ``day_date``.

    Returns ``(session, created)``. Repeating the request returns the session
    made the first time. The session is a copy of what was planned, so later
    edits of the plan leave the history alone.
    """
    if day_key not in plan_days.WEEKDAYS:
        raise PlanConflict("unknown_day")
    planned = day_exercises(plan, day_key)
    if not planned:
        raise PlanConflict("rest_day")

    existing = TrainingSession.query.filter_by(plan_id=plan.id, plan_date=day_date).first()
    if existing is not None:
        return existing, False

    catalog = catalog_service.exercises_by_id(
        item["exercise"]["id"] for item in planned if isinstance(item.get("exercise"), dict)
    )
    session = TrainingSession(
        user_id=plan.user_id,
        status="active",
        started_at=performed_at,
        plan_id=plan.id,
        plan_day=day_key,
        plan_date=day_date,
    )
    try:
        with db.session.begin_nested():
            db.session.add(session)
            db.session.flush()
    except IntegrityError:
        return TrainingSession.query.filter_by(plan_id=plan.id, plan_date=day_date).one(), False

    for item in planned:
        exercise = catalog.get((item.get("exercise") or {}).get("id"))
        if exercise is None:
            continue
        done = session_update_fields(
            exercise,
            {
                "sets_done": item.get("sets"),
                "reps_done": item.get("reps"),
                "duration_sec_done": item.get("duration_sec"),
                "load_done": item.get("load") or 0,
            },
        )
        row = SessionExercise(session_id=session.id, exercise_id=exercise.id, **done)
        row.sets_planned = row.sets_done
        row.reps_planned = row.reps_done
        row.duration_sec_planned = row.duration_sec_done
        row.load_planned = row.load_done
        db.session.add(row)
    db.session.flush()
    db.session.refresh(session)

    # Also adds the session's load to the user's cumulative training load.
    TrainingSessionService.finish_session(session, finished_at=performed_at)
    return session, True
