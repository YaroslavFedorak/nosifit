from datetime import date
from .score import calculate_daily_score


def _import(name):
    module = __import__(name, fromlist=["*"])
    return module


def _call(func, *args, **kwargs):
    return func(*args, **kwargs)


def get_today_overview(user_id):
    today = date.today().isoformat()
    training = {}
    nutrition = {}
    recovery = {}

    try:
        mod = _import("myapp.app.services.training_load_service")
        svc = getattr(mod, "TrainingLoadService", None)
        if svc and hasattr(svc, "get_daily_summary"):
            training = _call(svc.get_daily_summary, user_id) or {}
    except Exception:
        raise

    try:
        mod = _import("myapp.app.services.nutrition.stats_service")
        svc = getattr(mod, "NutritionStatsService", None)
        if svc and hasattr(svc, "get_daily_summary"):
            nutrition = _call(svc.get_daily_summary, user_id) or {}
    except Exception:
        raise

    try:
        mod = _import("myapp.app.services.recovery.snapshot_service")
        svc = getattr(mod, "RecoverySnapshotService", None)
        if svc and hasattr(svc, "get_daily_summary"):
            recovery = _call(svc.get_daily_summary, user_id) or {}
    except Exception:
        raise

    training_score = training.get("score") if isinstance(training, dict) else None
    nutrition_score = nutrition.get("score") if isinstance(nutrition, dict) else None
    recovery_score = recovery.get("score") if isinstance(recovery, dict) else None

    daily_score = calculate_daily_score(training_score, nutrition_score, recovery_score)

    training_payload = {
        "score": training_score if training_score is not None else None,
        "completed": (
            training.get("completed", False) if isinstance(training, dict) else False
        ),
        "duration": training.get("duration", 0) if isinstance(training, dict) else 0,
        "exercise_count": (
            training.get("exercise_count", 0) if isinstance(training, dict) else 0
        ),
    }

    nutrition_payload = {
        "score": nutrition_score if nutrition_score is not None else None,
        "calories": nutrition.get("calories", 0) if isinstance(nutrition, dict) else 0,
        "protein": nutrition.get("protein", 0) if isinstance(nutrition, dict) else 0,
        "water": nutrition.get("water", 0) if isinstance(nutrition, dict) else 0,
    }

    recovery_payload = {
        "score": recovery_score if recovery_score is not None else None,
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
        "date": today,
        "daily_score": daily_score,
        "training": training_payload,
        "nutrition": nutrition_payload,
        "recovery": recovery_payload,
    }


def get_heatmap(user_id):
    try:
        tmod = _import("myapp.app.services.training_load_service")
        tsvc = getattr(tmod, "TrainingLoadService", None)
    except Exception:
        raise
    try:
        nmod = _import("myapp.app.services.nutrition.stats_service")
        nsvc = getattr(nmod, "NutritionStatsService", None)
    except Exception:
        raise
    try:
        rmod = _import("myapp.app.services.recovery.snapshot_service")
        rsvc = getattr(rmod, "RecoverySnapshotService", None)
    except Exception:
        raise

    t_days = {}
    n_days = {}
    r_days = {}

    if tsvc and hasattr(tsvc, "get_month_scores"):
        t_days = _call(tsvc.get_month_scores, user_id) or {}
    if nsvc and hasattr(nsvc, "get_month_scores"):
        n_days = _call(nsvc.get_month_scores, user_id) or {}
    if rsvc and hasattr(rsvc, "get_month_scores"):
        r_days = _call(rsvc.get_month_scores, user_id) or {}

    keys = set()
    if isinstance(t_days, dict):
        keys.update(t_days.keys())
    if isinstance(n_days, dict):
        keys.update(n_days.keys())
    if isinstance(r_days, dict):
        keys.update(r_days.keys())

    result = []
    for d in sorted(keys):
        t = t_days.get(d) if isinstance(t_days, dict) else None
        n = n_days.get(d) if isinstance(n_days, dict) else None
        r = r_days.get(d) if isinstance(r_days, dict) else None
        daily = calculate_daily_score(t, n, r)
        result.append(
            {
                "date": d,
                "daily_score": daily,
                "training": t if t is not None else None,
                "nutrition": n if n is not None else None,
                "recovery": r if r is not None else None,
            }
        )
    return result
