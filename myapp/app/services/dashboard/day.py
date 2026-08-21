from datetime import datetime

from .score import calculate_daily_score


def _import(name):
    return __import__(name, fromlist=["*"])


def get_day_details(user_id, day_iso):
    try:
        datetime.fromisoformat(day_iso)
    except (TypeError, ValueError):
        return None

    training = None
    nutrition = None
    recovery = None

    try:
        module = _import("myapp.app.services.training.load_service")

        service = getattr(
            module,
            "TrainingLoadService",
            None,
        )

        if service and hasattr(service, "get_day_summary"):
            training = service.get_day_summary(
                user_id,
                day_iso,
            )
        elif service and hasattr(service, "get_daily_summary"):
            training = service.get_daily_summary(
                user_id,
                day_iso,
            )
    except Exception:
        training = None

    try:
        module = _import("myapp.app.services.nutrition.stats_service")

        service = getattr(
            module,
            "NutritionStatsService",
            None,
        )

        if service and hasattr(service, "get_day_summary"):
            nutrition = service.get_day_summary(
                user_id,
                day_iso,
            )
        elif service and hasattr(service, "get_daily_summary"):
            nutrition = service.get_daily_summary(
                user_id,
                day_iso,
            )
    except Exception:
        nutrition = None

    try:
        module = _import("myapp.app.services.recovery.snapshot_service")

        service = getattr(
            module,
            "RecoverySnapshotService",
            None,
        )

        if service and hasattr(service, "get_day_summary"):
            recovery = service.get_day_summary(
                user_id,
                day_iso,
            )
        elif service and hasattr(service, "get_daily_summary"):
            recovery = service.get_daily_summary(
                user_id,
                day_iso,
            )
    except Exception:
        recovery = None

    training_score = training.get("score") if isinstance(training, dict) else None

    nutrition_score = nutrition.get("score") if isinstance(nutrition, dict) else None

    recovery_score = recovery.get("score") if isinstance(recovery, dict) else None

    daily_score = calculate_daily_score(
        training_score,
        nutrition_score,
        recovery_score,
    )

    training_payload = {
        "score": training_score,
        "completed": (
            training.get("completed", False) if isinstance(training, dict) else False
        ),
        "duration": (training.get("duration", 0) if isinstance(training, dict) else 0),
        "exercise_count": (
            training.get("exercise_count", 0) if isinstance(training, dict) else 0
        ),
    }

    nutrition_payload = {
        "score": nutrition_score,
        "calories": (
            nutrition.get("calories", 0) if isinstance(nutrition, dict) else 0
        ),
        "protein": (nutrition.get("protein", 0) if isinstance(nutrition, dict) else 0),
        "water": (nutrition.get("water", 0) if isinstance(nutrition, dict) else 0),
    }

    recovery_payload = {
        "score": recovery_score,
        "sleep_hours": (
            recovery.get("sleep_hours", 0) if isinstance(recovery, dict) else 0
        ),
        "habits_completed": (
            recovery.get("habits_completed", 0) if isinstance(recovery, dict) else 0
        ),
        "habits_total": (
            recovery.get("habits_total", 0) if isinstance(recovery, dict) else 0
        ),
    }

    return {
        "date": day_iso,
        "daily_score": daily_score,
        "training": training_payload,
        "nutrition": nutrition_payload,
        "recovery": recovery_payload,
    }
