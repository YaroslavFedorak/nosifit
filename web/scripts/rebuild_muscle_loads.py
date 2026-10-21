"""Rebuild TrainingSession.muscle_loads (muscle -> effective sets) from the
logged exercises of finished sessions.

Only sessions whose stored value is not a valid {muscle_slug: number} map are
touched, so the script is safe to run again. Pass --all to recompute every
finished session.
"""

import sys

from web.app import create_app
from backend.app.extensions import db
from backend.app.models.training_session import TrainingSession
from backend.app.services.training.model import TrainingModelService
from backend.app.training.exercises.catalog import known_muscle_slugs


def needs_rebuild(value):
    if not isinstance(value, dict) or not value:
        return True
    return any(key not in known_muscle_slugs() for key in value)


def rebuild(rebuild_all=False):
    """Rebuild inside the current app context; returns (changed, total)."""
    changed = 0
    sessions = TrainingSession.query.filter_by(status="finished").all()
    for session in sessions:
        if not rebuild_all and not needs_rebuild(session.muscle_loads):
            continue
        session.muscle_loads = TrainingModelService.session_summary(session)["muscle_sets"]
        changed += 1
    db.session.commit()
    return changed, len(sessions)


def run(rebuild_all=False):
    app = create_app()
    with app.app_context():
        changed, total = rebuild(rebuild_all)
        print(f"Rebuilt muscle_loads for {changed} of {total} finished sessions")


if __name__ == "__main__":
    run(rebuild_all="--all" in sys.argv[1:])
