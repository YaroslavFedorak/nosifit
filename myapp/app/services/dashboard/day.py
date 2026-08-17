from datetime import datetime
from .score import calculate_daily_score


def _import(name):
    module = __import__(name, fromlist=["*"])
    return module


def get_day_details(user_id, day_iso):
    try:
        datetime.fromisoformat(day_iso)
    except Exception:
        return None

    t = None
    n = None
    r = None

    try:
        tmod = _import("myapp.app.services.training.load_service")
        tsvc = getattr(tmod, "TrainingLoadService", None)
        if tsvc and hasattr(tsvc, "get_day_summary"):
            t = tsvc.get_day_summary(user_id, day_iso)
        elif tsvc and hasattr(tsvc, "get_daily_summary"):
            t = tsvc.get_daily_summary(user_id, day_iso)
    except Exception:
        t = None

    try:
        nmod = _import("myapp.app.services.nutrition.stats_service")
        nsvc = getattr(nmod, "NutritionStatsService", None)
        if nsvc and hasattr(nsvc, "get_day_summary"):
            n = nsvc.get_day_summary(user_id, day_iso)
        elif nsvc and hasattr(nsvc, "get_daily_summary"):
            n = nsvc.get_daily_summary(user_id, day_iso)
    except Exception:
        n = None

    try:
        rmod = _import("myapp.app.services.recovery.snapshot_service")
        rsvc = getattr(rmod, "RecoverySnapshotService", None)
        if rsvc and hasattr(rsvc, "get_day_summary"):
            r = rsvc.get_day_summary(user_id, day_iso)
        elif rsvc and hasattr(rsvc, "get_daily_summary"):
            r = rsvc.get_daily_summary(user_id, day_iso)
    except Exception:
        r = None

    t_score = t.get("score") if isinstance(t, dict) else None
    n_score = n.get("score") if isinstance(n, dict) else None
    r_score = r.get("score") if isinstance(r, dict) else None

    daily_score = calculate_daily_score(t_score, n_score, r_score)

    training_payload = {
        "score": t_score if t_score is not None else None,
        "completed": t.get("completed", False) if isinstance(t, dict) else False,
        "duration": t.get("duration", 0) if isinstance(t, dict) else 0,
        "exercise_count": t.get("exercise_count", 0) if isinstance(t, dict) else 0,
    }

    nutrition_payload = {
        "score": n_score if n_score is not None else None,
        "calories": n.get("calories", 0) if isinstance(n, dict) else 0,
        "protein": n.get("protein", 0) if isinstance(n, dict) else 0,
        "water": n.get("water", 0) if isinstance(n, dict) else 0,
    }

    recovery_payload = {
        "score": r_score if r_score is not None else None,
        "sleep_hours": r.get("sleep_hours", 0) if isinstance(r, dict) else 0,
        "habits_completed": r.get("habits_completed", 0) if isinstance(r, dict) else 0,
        "habits_total": r.get("habits_total", 0) if isinstance(r, dict) else 0,
    }

    return {
        "date": day_iso,
        "daily_score": daily_score,
        "training": training_payload,
        "nutrition": nutrition_payload,
        "recovery": recovery_payload,
    }
