"""Strength tests and the user's training preferences."""

from backend.app.extensions import db
from backend.app.training.models.performance_state import PerformanceState
from backend.app.training.models.user_pref import UserPreference


def latest_performance(user):
    return user.performance_states.order_by(PerformanceState.created_at.desc()).first()


def record_strength_test(user_id, *, pushups, squats, situps):
    perf = PerformanceState(
        user_id=user_id,
        pushups=pushups,
        squats=squats,
        situps=situps,
    )
    db.session.add(perf)
    db.session.commit()
    return perf


def training_preferences(user_id) -> dict:
    """key -> value of the user's stored preferences (injuries, equipment)."""
    return {p.key: p.value for p in UserPreference.query.filter_by(user_id=user_id)}
