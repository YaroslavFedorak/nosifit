from datetime import datetime


def calculate_training_score(session):
    if not session or session.status != "finished":
        return None

    exercise_count = len(session.exercises)

    if exercise_count == 0:
        return 0

    duration = _duration(session)
    internal_load = float(session.internal_load or 0)

    exercise_score = min(exercise_count / 8.0, 1.0) * 35
    duration_score = min(duration / 90.0, 1.0) * 25
    load_score = min(internal_load / 500.0, 1.0) * 40

    score = exercise_score + duration_score + load_score

    return max(
        0,
        min(
            100,
            int(round(score)),
        ),
    )


def analyze_muscles(muscle_loads):
    if not isinstance(muscle_loads, dict):
        return {
            "weak": [],
            "balanced": [],
            "overloaded": [],
        }

    values = {}

    for muscle, load in muscle_loads.items():
        try:
            value = float(load or 0)
        except (TypeError, ValueError):
            continue

        if value >= 0:
            values[str(muscle)] = value

    positive = [value for value in values.values() if value > 0]

    if not positive:
        return {
            "weak": [],
            "balanced": [],
            "overloaded": [],
        }

    average = sum(positive) / len(positive)

    weak = []
    balanced = []
    overloaded = []

    for muscle, value in sorted(
        values.items(),
        key=lambda item: item[1],
    ):
        if value < average * 0.55:
            weak.append(muscle)
        elif value > average * 1.6:
            overloaded.append(muscle)
        else:
            balanced.append(muscle)

    return {
        "weak": weak[:6],
        "balanced": balanced[:6],
        "overloaded": overloaded[:6],
    }


def _duration(session):
    if not session.started_at:
        return 0

    end = session.finished_at or datetime.utcnow()

    seconds = (end - session.started_at).total_seconds()

    if seconds <= 0:
        return 0

    return int(round(seconds / 60))
