from datetime import datetime, date
from flask import Blueprint, request, jsonify
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
    return jsonify({"created": created})


@recovery_bp.delete("/habits/<int:user_habit_id>")
def remove_habit(user_habit_id):
    habit = habit_service.remove_user_habit(user_habit_id)
    if habit is None:
        return jsonify({"error": "habit not found"}), 404
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

    for r in recs:
        habit_service.ensure_user_has_habit(user_id, r["habit_id"])

    return (
        jsonify({"recovery_score": snapshot.recovery_score, "recommendations": recs}),
        200,
    )
