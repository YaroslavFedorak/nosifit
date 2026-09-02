from .dto import training_summary_to_dict
from .metrics import calculate_training_score, analyze_muscles


class TrainingDashboardAnalyzer:

    @staticmethod
    def analyze_session(session):
        if not session:
            return training_summary_to_dict()

        return training_summary_to_dict(
            score=calculate_training_score(session),
            completed=session.status == "finished",
            duration=_duration(session),
            exercise_count=len(session.exercises),
            internal_load=session.internal_load or 0,
        )

    @staticmethod
    def analyze_muscles(session):
        if not session:
            return {
                "weak": [],
                "balanced": [],
                "overloaded": [],
            }

        return analyze_muscles(session.muscle_loads or {})

    @staticmethod
    def build_widget(session):
        return {
            **TrainingDashboardAnalyzer.analyze_session(session),
            "muscles": TrainingDashboardAnalyzer.analyze_muscles(session),
        }


def _duration(session):
    if not session.started_at:
        return 0

    from datetime import datetime

    end = session.finished_at or datetime.utcnow()

    seconds = (end - session.started_at).total_seconds()

    if seconds <= 0:
        return 0

    return int(round(seconds / 60))
