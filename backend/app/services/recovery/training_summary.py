"""Training part of a recovery day: readiness and the day's hard sets."""

from flask import current_app

from backend.app.extensions import db
from backend.app.models.user import User
from backend.app.services.training.model import TrainingModelService
from backend.app.services.training.model.readiness import readiness_level


def training_day_summary(user_id, day, readiness_score=None):
    """Training part of the day details: readiness level (score kept for the
    bar) and the day's hard sets. The legacy 'load' number is no longer sent."""
    summary = {
        "readiness_score": readiness_score,
        "readiness_level": None,
        "hard_sets": 0.0,
        "session_training_stress_proxy": 0.0,
    }
    try:
        if readiness_score is None:
            user = db.session.get(User, user_id)
            if user is not None:
                readiness_score = TrainingModelService.training_readiness_score(user, day)
        stress = TrainingModelService.day_stress(user_id, day)
        summary.update(
            readiness_score=readiness_score,
            readiness_level=(
                readiness_level(readiness_score / 100.0)
                if readiness_score is not None
                else None
            ),
            hard_sets=stress["hard_sets"],
            session_training_stress_proxy=stress["session_training_stress_proxy"],
        )
    except Exception:
        current_app.logger.exception(
            "Error while building training summary for user %s date %s", user_id, day
        )
    return summary
