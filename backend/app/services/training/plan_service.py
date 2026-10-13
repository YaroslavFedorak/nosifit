"""A user's training plans. Only one plan is active at a time."""

from backend.app.extensions import db
from backend.app.training.models.training_plan import TrainingPlan


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
