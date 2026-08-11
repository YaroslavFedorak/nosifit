from datetime import datetime, date
from flask import Blueprint, request, jsonify, current_app
from myapp.app.services.recovery import (
    SleepService,
    HabitService,
    SnapshotService,
    StatsService,
    RecommendationService,
)
from myapp.app.models.recovery.habit import RecoveryHabit

recovery_bp = Blueprint("recovery", __name__, url_prefix="/api/recovery")

sleep_service = SleepService()
habit_service = HabitService()
snapshot_service = SnapshotService()
stats_service = StatsService()


def parse_iso(dt: str) -> datetime:
    if dt.endswith("Z"):
        dt = dt.replace("Z", "+00:00")
    return datetime.fromisoformat(dt)


@recovery_bp.post("/sleep")
def add_sleep():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    sleep_start = data.get("sleep_start")
    sleep_end = data.get("sleep_end")

    if user_id is None or sleep_start is None or sleep_end is None:
        return (
            jsonify({"error": "user_id, sleep_start and sleep_end are required"}),
            400,
        )

    try:
        start_dt = parse_iso(sleep_start)
        end_dt = parse_iso(sleep_end)
    except ValueError:
        return jsonify({"error": "Invalid datetime format"}), 400

    if end_dt <= start_dt:
        return jsonify({"error": "sleep_end must be after sleep_start"}), 400

    entry = sleep_service.add_sleep(user_id, start_dt, end_dt)
    snapshot_service.generate_snapshot(user_id)

    return (
        jsonify(
            {
                "id": entry.id,
                "duration_minutes": entry.duration_minutes,
                "quality_score": entry.quality_score,
            }
        ),
        201,
    )


@recovery_bp.get("/habits/list")
def get_habits_list():
    habits = (
        RecoveryHabit.query.filter_by(is_active=True, is_archived=False)
        .order_by(RecoveryHabit.sort_order.asc(), RecoveryHabit.id.asc())
        .all()
    )

    return jsonify(
        [
            {
                "id": h.id,
                "slug": h.slug,
                "name": h.name,
                "description": h.description,
                "category": h.category,
                "points": h.points,
                "icon": h.icon,
                "recommended_when": h.recommended_when,
                "premium_only": h.premium_only,
            }
            for h in habits
        ]
    )


@recovery_bp.get("/habits/user/<int:user_id>")
def get_user_habits(user_id):
    habits = habit_service.get_user_habits_full(user_id)
    return jsonify(
        [
            {
                "id": h.id,
                "name": h.name,
                "category": h.category,
                "points": h.points,
                "icon": h.icon,
            }
            for h in habits
        ]
    )


@recovery_bp.post("/habits/add/<int:habit_id>")
def add_habit(habit_id):
    user_id = request.json.get("user_id")
    habit, created = habit_service.add_user_habit(user_id, habit_id)

    if created:
        snapshot_service.generate_snapshot(user_id)

    return jsonify({"created": created})


@recovery_bp.delete("/habits/<int:user_habit_id>")
def remove_habit(user_habit_id):
    habit = habit_service.remove_user_habit(user_habit_id)
    if habit is None:
        return jsonify({"error": "habit not found"}), 404

    snapshot_service.generate_snapshot(habit.user_id)

    return jsonify({"removed": user_habit_id}), 200


@recovery_bp.post("/habits/logs")
def log_habit():
    data = request.get_json(silent=True) or {}
    user_habit_id = data.get("user_habit_id")

    if user_habit_id is None:
        return jsonify({"error": "user_habit_id is required"}), 400

    log = habit_service.log_habit(user_habit_id)
    if log is None:
        return jsonify({"error": "user_habit not found"}), 404

    user_id = log.user_id
    snapshot = snapshot_service.generate_snapshot(user_id)

    return jsonify({"logged": log.id, "snapshot": snapshot.to_dict()}), 200


@recovery_bp.get("/snapshot/<int:user_id>")
def get_snapshot(user_id):
    raw_date = request.args.get("date")
    if raw_date:
        try:
            dt = datetime.fromisoformat(raw_date).date()
        except ValueError:
            return jsonify({"error": "Invalid date format"}), 400
        snapshot = stats_service.get_daily_snapshot(user_id, dt)
    else:
        snapshot = stats_service.get_last_snapshot(user_id)

    if snapshot is None:
        return jsonify({"snapshot": None}), 200

    habits = habit_service.get_user_habits_with_status(user_id)

    recs = RecommendationService().build_recommendations(
        snapshot.sleep_score,
        snapshot.recovery_score,
        snapshot.energy_score,
        snapshot.habit_score,
        snapshot.training_score,
    )

    return (
        jsonify(
            {
                **snapshot.to_dict(),
                "sleep_score": int(snapshot.sleep_score or 0),
                "habit_score": int(snapshot.habit_score or 0),
                "training_score": int(snapshot.training_score or 0),
                "energy_score": int(snapshot.energy_score or 0),
                "recovery_score": int(snapshot.recovery_score or 0),
                "habits": habits,
                "recommendations": recs,
            }
        ),
        200,
    )


@recovery_bp.get("/heatmap/<int:user_id>")
def get_heatmap(user_id):
    raw_year = request.args.get("year")
    try:
        year = int(raw_year) if raw_year is not None else date.today().year
    except ValueError:
        return jsonify({"error": "year must be integer"}), 400

    heatmap = stats_service.get_heatmap(user_id, year)

    return (
        jsonify(
            {
                "days": [
                    {
                        "date": s.date.isoformat(),
                        "recovery_score": s.recovery_score,
                        "energy_score": s.energy_score,
                        "level": getattr(s, "level", 0),
                    }
                    for s in heatmap
                ]
            }
        ),
        200,
    )


@recovery_bp.get("/recommendations/<int:user_id>")
def get_recommendations(user_id):
    snapshot = stats_service.get_last_snapshot(user_id)
    if snapshot is None:
        return jsonify({"recovery_score": None, "recommendations": []}), 200

    recs = RecommendationService().build_recommendations(
        snapshot.sleep_score,
        snapshot.recovery_score,
        snapshot.energy_score,
        snapshot.habit_score,
        snapshot.training_score,
    )

    return (
        jsonify({"recovery_score": snapshot.recovery_score, "recommendations": recs}),
        200,
    )


@recovery_bp.get("/day-details/<int:user_id>")
def get_day_details(user_id):
    raw_date = request.args.get("date")
    if not raw_date:
        return jsonify({"error": "date is required"}), 400

    try:
        dt = datetime.fromisoformat(raw_date).date()
    except ValueError:
        return jsonify({"error": "Invalid date format"}), 400

    try:
        snapshot = stats_service.get_daily_snapshot(user_id, dt)
    except Exception:
        current_app.logger.exception(
            "Error while fetching daily snapshot for user %s date %s", user_id, raw_date
        )
        snapshot = None

    try:
        if snapshot is not None:
            try:
                habits = habit_service.get_user_habits_with_status(user_id)
            except Exception:
                current_app.logger.exception(
                    "Error while fetching user habits for user %s", user_id
                )
                habits = []

            try:
                recs = RecommendationService().build_recommendations(
                    snapshot.sleep_score,
                    snapshot.recovery_score,
                    snapshot.energy_score,
                    snapshot.habit_score,
                    snapshot.training_score,
                )
            except Exception:
                current_app.logger.exception(
                    "Error while building recommendations for user %s", user_id
                )
                recs = []

            base = {
                **snapshot.to_dict(),
                "sleep_score": int(snapshot.sleep_score or 0),
                "habit_score": int(snapshot.habit_score or 0),
                "training_score": int(snapshot.training_score or 0),
                "energy_score": int(snapshot.energy_score or 0),
                "recovery_score": int(snapshot.recovery_score or 0),
                "habits": habits,
                "recommendations": recs,
            }

            return (
                jsonify(
                    {
                        "date": raw_date,
                        "has_data": True,
                        "recovery": {
                            "score": base.get("recovery_score"),
                            "status": None,
                            "energy_score": base.get("energy_score"),
                        },
                        "sleep": {
                            "duration_minutes": base.get("sleep_duration_minutes"),
                            "quality_score": base.get("sleep_score"),
                            "bedtime": base.get("sleep_start"),
                            "wake_time": base.get("sleep_end"),
                        },
                        "training": {
                            "load": base.get("training_score"),
                            "sessions": base.get("training_sessions", 0),
                            "exercises": base.get("training_exercises", []),
                        },
                        "habits": {
                            "completed": len(
                                [
                                    h
                                    for h in base.get("habits", [])
                                    if h.get("completed")
                                ]
                            ),
                            "total": len(base.get("habits", [])),
                            "score": base.get("habit_score"),
                            "items": base.get("habits", []),
                        },
                        "recommendations": {
                            "completed": len(
                                [
                                    r
                                    for r in base.get("recommendations", [])
                                    if r.get("followed")
                                ]
                            ),
                            "total": len(base.get("recommendations", [])),
                            "items": base.get("recommendations", []),
                        },
                    }
                ),
                200,
            )

        # snapshot is None — try to collect data safely
        try:
            habits = habit_service.get_user_habits_with_status(user_id)
        except Exception:
            current_app.logger.exception(
                "Error while fetching user habits (fallback) for user %s", user_id
            )
            habits = []

        try:
            recs = RecommendationService().build_recommendations(0, 0, 0, 0, 0)
        except Exception:
            current_app.logger.exception(
                "Error while building recommendations (fallback) for user %s", user_id
            )
            recs = []

        sleep_entry = None
        try:
            if hasattr(sleep_service, "get_sleep_for_date"):
                sleep_entry = sleep_service.get_sleep_for_date(user_id, dt)
            elif hasattr(sleep_service, "get_sleep_by_date"):
                sleep_entry = sleep_service.get_sleep_by_date(user_id, dt)
        except Exception:
            current_app.logger.exception(
                "Error while fetching sleep entry for user %s date %s",
                user_id,
                raw_date,
            )
            sleep_entry = None

        training_exercises = []
        training_load = None
        training_sessions = 0

        has_any = bool(
            (sleep_entry is not None)
            or (habits and len(habits) > 0)
            or (recs and len(recs) > 0)
            or (training_exercises and len(training_exercises) > 0)
        )

        return (
            jsonify(
                {
                    "date": raw_date,
                    "has_data": has_any,
                    "recovery": {"score": None, "status": None, "energy_score": None},
                    "sleep": {
                        "duration_minutes": (
                            getattr(sleep_entry, "duration_minutes", None)
                            if sleep_entry
                            else None
                        ),
                        "quality_score": (
                            getattr(sleep_entry, "quality_score", None)
                            if sleep_entry
                            else None
                        ),
                        "bedtime": (
                            getattr(sleep_entry, "start_iso", None)
                            if sleep_entry
                            else None
                        ),
                        "wake_time": (
                            getattr(sleep_entry, "end_iso", None)
                            if sleep_entry
                            else None
                        ),
                    },
                    "training": {
                        "load": training_load,
                        "sessions": training_sessions,
                        "exercises": training_exercises,
                    },
                    "habits": {
                        "completed": (
                            len([h for h in habits if h.get("completed")])
                            if habits
                            else 0
                        ),
                        "total": len(habits) if habits else 0,
                        "score": None,
                        "items": habits or [],
                    },
                    "recommendations": {
                        "completed": (
                            len([r for r in recs if r.get("followed")]) if recs else 0
                        ),
                        "total": len(recs) if recs else 0,
                        "items": recs or [],
                    },
                }
            ),
            200,
        )
    except Exception:
        current_app.logger.exception(
            "Unhandled error in day-details endpoint for user %s date %s",
            user_id,
            raw_date,
        )
        return (
            jsonify(
                {
                    "date": raw_date,
                    "has_data": False,
                    "recovery": {"score": None, "status": None, "energy_score": None},
                    "sleep": {
                        "duration_minutes": None,
                        "quality_score": None,
                        "bedtime": None,
                        "wake_time": None,
                    },
                    "training": {"load": None, "sessions": 0, "exercises": []},
                    "habits": {"completed": 0, "total": 0, "score": None, "items": []},
                    "recommendations": {"completed": 0, "total": 0, "items": []},
                }
            ),
            200,
        )
