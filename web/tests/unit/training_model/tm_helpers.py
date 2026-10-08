"""Builders shared by the pure training-model tests."""

from datetime import datetime, timedelta

from backend.app.services.training.model.context import TrainingContext
from backend.app.services.training.model.records import LoggedEntry, SleepNight

NOW = datetime(2026, 10, 8, 18, 0)


def entry(slug, days_ago, sets, reps=10, rpe=8.0, load=0.0, session=None, duration=None, now=NOW):
    return LoggedEntry(
        session_id=session if session is not None else int(days_ago * 100) + 1,
        exercise_id=slug,
        performed_at=now - timedelta(days=days_ago),
        sets=sets,
        reps=reps,
        duration_sec=duration,
        load_kg=load,
        rpe=rpe,
    )


def nights(minutes_by_offset, now=NOW):
    """{0: 300, 1: 420} -> SleepNight list ending on now.date() - offset."""
    return [
        SleepNight(night=(now - timedelta(days=offset)).date(), minutes=minutes)
        for offset, minutes in minutes_by_offset.items()
    ]


def context(**overrides):
    values = dict(
        goal="hypertrophy",
        experience="intermediate",
        workouts_per_week=3,
        available_equipment=None,
        body_weight_kg=80.0,
    )
    values.update(overrides)
    return TrainingContext(**values)


def balanced_week(days_offset=0, sets=4, rpe=8.0):
    """A full-body routine covering all major muscles, three days a week."""
    base = days_offset
    return [
        entry("bench-press", base + 1, sets, 8, rpe, 60),
        entry("barbell-row", base + 1, sets, 10, rpe, 50),
        entry("barbell-back-squat", base + 1, sets, 6, rpe, 80),
        entry("overhead-press", base + 3, sets, 8, rpe, 35),
        entry("pull-ups", base + 3, sets, 8, rpe),
        entry("romanian-deadlift", base + 3, sets, 10, rpe, 60),
        entry("barbell-curl", base + 5, sets, 12, rpe, 25),
        entry("tricep-pushdown", base + 5, sets, 12, rpe, 25),
        entry("calf-raise", base + 5, sets, 15, rpe),
        entry("hanging-leg-raise", base + 5, sets, 12, rpe),
        entry("leg-curl", base + 5, sets, 12, rpe, 30),
    ]
