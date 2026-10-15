"""The nutrition targets of a user, today and on past days.

Reading targets never writes. They are calculated from the profile
(``calories_service``) and stored when they change - by the profile edit, the
new weight and onboarding, see ``record_goal_change`` - so a past day keeps
the targets it was lived with.

Targets that cannot be calculated (profile incomplete or outside the range
the formulas are valid for) are reported with ``available: False`` and zeros;
a zero target is never a goal.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select

from backend.app.extensions import db
from backend.app.models.nutrition.goal_history import NutritionGoalHistory
from backend.app.models.nutrition.user_goals import UserGoals
from backend.app.models.user import User
from backend.app.services.nutrition.calories_service import (
    calculate_nutrition_goals,
)

# About 14 g per 1000 kcal at a 2100 kcal diet (US Dietary Reference Intake).
DEFAULT_FIBER_GOAL = 30.0


def _unavailable(fiber=DEFAULT_FIBER_GOAL):
    return {
        "calories": 0,
        "protein": 0,
        "fat": 0,
        "carbs": 0,
        "fiber": fiber,
        "available": False,
        "source": "none",
    }


def get_goals(user_id):
    """Today's targets; no database writes."""
    user = db.session.get(User, user_id)
    stored = UserGoals.query.filter_by(user_id=user_id).first()
    fiber = (stored.fiber_goal if stored and stored.fiber_goal else DEFAULT_FIBER_GOAL)

    if user is None:
        return _unavailable(fiber)

    calculated = calculate_nutrition_goals(user)
    if calculated is not None:
        return {**calculated, "fiber": fiber, "available": True, "source": "profile"}

    # The profile cannot give targets any more; the last stored ones stay
    # visible instead of vanishing, marked as such.
    if stored and (stored.calories_goal or 0) > 0:
        return {
            "calories": stored.calories_goal,
            "protein": stored.protein_goal or 0,
            "fat": stored.fat_goal or 0,
            "carbs": stored.carb_goal or 0,
            "fiber": fiber,
            "available": True,
            "source": "stored",
        }
    return _unavailable(fiber)


def goals_timeline(user_id, start: date, end: date):
    """History rows that matter for ``start..end``, oldest first.

    Includes the last row before ``start`` (the targets in force on its first
    day), so one lookup resolves every day of the range. Rows exist only
    where the targets changed, so the single query stays small.
    """
    rows = db.session.execute(
        select(NutritionGoalHistory)
        .where(
            NutritionGoalHistory.user_id == user_id,
            NutritionGoalHistory.effective_from <= end,
        )
        .order_by(NutritionGoalHistory.effective_from.asc())
    ).scalars().all()
    before = [row for row in rows if row.effective_from < start]
    return before[-1:] + [row for row in rows if row.effective_from >= start]


def goals_for_day(timeline, current, day: date):
    """The targets for ``day`` from a timeline (see :func:`goals_timeline`).

    ``source`` says where they come from: ``history`` (stored for that day),
    or ``current`` when the day is before the first stored change - then
    today's targets are shown as they are and flagged ``estimated``, because
    what applied back then cannot be reconstructed.
    """
    row = None
    for candidate in timeline:
        if candidate.effective_from <= day:
            row = candidate
        else:
            break
    if row is None:
        return {**current, "source": "current", "estimated": True}
    return {
        "calories": row.calories,
        "protein": row.protein,
        "fat": row.fat,
        "carbs": row.carbs,
        "fiber": row.fiber,
        "available": row.calories > 0,
        "source": "history",
        "estimated": False,
    }


def get_goals_for_day(user_id, day: date, current=None):
    current = current if current is not None else get_goals(user_id)
    return goals_for_day(goals_timeline(user_id, day, day), current, day)
