from datetime import datetime, date

from flask import (
    Blueprint,
    request,
    jsonify,
    current_app,
)

from web.app.services.recovery import (
    SleepService,
    HabitService,
    SnapshotService,
    StatsService,
    RecommendationService,
)

from web.app.models.recovery.habit import RecoveryHabit
from web.app.services.training.load_service import TrainingLoadService

recovery_bp = Blueprint("recovery", __name__, url_prefix="/api/recovery")

sleep_service = SleepService()
habit_service = HabitService()
snapshot_service = SnapshotService()
stats_service = StatsService()
training_load_service = TrainingLoadService()
recommendation_service = RecommendationService()


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
            jsonify({"error": ("user_id, sleep_start " "and sleep_end are required")}),
            400,
        )

    try:
        start_dt = parse_iso(sleep_start)
        end_dt = parse_iso(sleep_end)
    except ValueError:
        return jsonify({"error": "Invalid datetime format"}), 400

    if end_dt <= start_dt:
        return jsonify({"error": ("sleep_end must be " "after sleep_start")}), 400

    entry = sleep_service.add_sleep(user_id, start_dt, end_dt)

    snapshot = snapshot_service.generate_snapshot(user_id, target_date=end_dt.date())

    return (
        jsonify(
            {
                "id": entry.id,
                "duration_minutes": (entry.duration_minutes),
                "quality_score": (snapshot.sleep_score if snapshot else 0),
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
                "id": habit.id,
                "slug": habit.slug,
                "name": habit.name,
                "description": habit.description,
                "category": habit.category,
                "points": habit.points,
                "icon": habit.icon,
                "recommended_when": (habit.recommended_when),
                "premium_only": (habit.premium_only),
            }
            for habit in habits
        ]
    )


@recovery_bp.get("/habits/user/<int:user_id>")
def get_user_habits(user_id):
    habits = habit_service.get_user_habits_with_status(user_id, date.today())

    return jsonify(habits)


@recovery_bp.post("/habits/add/<int:habit_id>")
def add_habit(habit_id):
    data = request.get_json(silent=True) or {}

    user_id = data.get("user_id")

    if user_id is None:
        return jsonify({"error": "user_id is required"}), 400

    habit, created = habit_service.add_user_habit(user_id, habit_id)

    if created:
        snapshot_service.generate_snapshot(user_id, target_date=date.today())

    return jsonify({"created": created, "user_habit_id": habit.id})


@recovery_bp.delete("/habits/<int:user_habit_id>")
def remove_habit(user_habit_id):
    habit = habit_service.remove_user_habit(user_habit_id)

    if habit is None:
        return jsonify({"error": "habit not found"}), 404

    snapshot_service.generate_snapshot(habit.user_id, target_date=date.today())

    return jsonify({"removed": user_habit_id}), 200


@recovery_bp.post("/habits/logs")
def log_habit():
    data = request.get_json(silent=True) or {}

    user_habit_id = data.get("user_habit_id")

    if user_habit_id is None:
        return jsonify({"error": ("user_habit_id is required")}), 400

    try:
        user_habit_id = int(user_habit_id)
    except (TypeError, ValueError):
        return jsonify({"error": ("user_habit_id " "must be integer")}), 400

    log = habit_service.log_habit(user_habit_id)

    if log is None:
        return jsonify({"error": ("user_habit not found")}), 404

    user_id = log.user_id

    snapshot = snapshot_service.generate_snapshot(user_id, target_date=date.today())

    return (
        jsonify(
            {
                "logged": log.id,
                "completed": True,
                "snapshot": (snapshot.to_dict() if snapshot else None),
            }
        ),
        200,
    )


@recovery_bp.delete("/habits/logs/<int:user_habit_id>")
def unlog_habit(user_habit_id):
    result = habit_service.unlog_habit(user_habit_id)

    if result is None:
        return jsonify({"error": ("user_habit not found")}), 404

    return jsonify({"removed": user_habit_id, "completed": False}), 200


@recovery_bp.get("/snapshot/<int:user_id>")
def get_snapshot(user_id):
    raw_date = request.args.get("date")

    if raw_date:
        try:
            dt = datetime.fromisoformat(raw_date).date()
        except ValueError:
            return jsonify({"error": ("Invalid date format")}), 400

        snapshot = stats_service.get_daily_snapshot(user_id, dt)
    else:
        snapshot = stats_service.get_last_snapshot(user_id)

    if snapshot is None:
        return jsonify({"snapshot": None}), 200

    habits = habit_service.get_user_habits_with_status(user_id, snapshot.date)

    daily_load = training_load_service.get_daily_load(user_id, target_day=snapshot.date)

    recs = recommendation_service.build_recommendations(
        user_id=user_id,
        sleep_score=snapshot.sleep_score,
        recovery_score=snapshot.recovery_score,
        energy_score=snapshot.energy_score,
        habit_score=snapshot.habit_score,
        daily_load=daily_load,
        target_date=snapshot.date,
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
                "recommendations": {
                    "total": len(recs),
                    "items": recs,
                },
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
        return jsonify({"error": ("year must be integer")}), 400

    heatmap = stats_service.get_heatmap(user_id, year)

    return (
        jsonify(
            {
                "days": [
                    {
                        "date": (snapshot.date.isoformat()),
                        "recovery_score": (snapshot.recovery_score),
                        "level": getattr(snapshot, "level", 0),
                    }
                    for snapshot in heatmap
                ]
            }
        ),
        200,
    )


@recovery_bp.get("/recommendations/<int:user_id>")
def get_recommendations(user_id):
    raw_date = request.args.get("date")

    if raw_date:
        try:
            target_date = datetime.fromisoformat(raw_date).date()
        except ValueError:
            return jsonify({"error": ("Invalid date format")}), 400
    else:
        target_date = date.today()

    snapshot = stats_service.get_daily_snapshot(user_id, target_date)

    if snapshot is None:
        snapshot = snapshot_service.generate_snapshot(user_id, target_date=target_date)

    daily_load = training_load_service.get_daily_load(user_id, target_day=target_date)

    recs = recommendation_service.build_recommendations(
        user_id=user_id,
        sleep_score=snapshot.sleep_score,
        recovery_score=snapshot.recovery_score,
        energy_score=snapshot.energy_score,
        habit_score=snapshot.habit_score,
        daily_load=daily_load,
        target_date=target_date,
    )

    return (
        jsonify(
            {
                "recovery_score": (snapshot.recovery_score),
                "recommendations": {
                    "total": len(recs),
                    "items": recs,
                },
            }
        ),
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
            "Error while fetching daily snapshot for user %s date %s",
            user_id,
            raw_date,
        )
        snapshot = None

    try:
        if snapshot is not None:
            try:
                habits = habit_service.get_user_habits_with_status(user_id, dt)
            except Exception:
                current_app.logger.exception(
                    "Error while fetching user habits for user %s",
                    user_id,
                )
                habits = []

            try:
                daily_load = training_load_service.get_daily_load(
                    user_id, target_day=dt
                )
            except Exception:
                current_app.logger.exception(
                    "Error while fetching daily load for user %s date %s",
                    user_id,
                    raw_date,
                )
                daily_load = None

            try:
                recs = recommendation_service.build_recommendations(
                    user_id=user_id,
                    sleep_score=snapshot.sleep_score,
                    recovery_score=snapshot.recovery_score,
                    energy_score=snapshot.energy_score,
                    habit_score=snapshot.habit_score,
                    daily_load=daily_load,
                    target_date=dt,
                )
            except Exception:
                current_app.logger.exception(
                    "Error while building recommendations for user %s",
                    user_id,
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
                                [habit for habit in habits if habit.get("completed")]
                            ),
                            "total": len(habits),
                            "score": base.get("habit_score"),
                            "items": habits,
                        },
                        "recommendations": {
                            "total": len(recs),
                            "items": recs,
                        },
                    }
                ),
                200,
            )

        try:
            habits = habit_service.get_user_habits_with_status(user_id, dt)
        except Exception:
            current_app.logger.exception(
                "Error while fetching user habits (fallback) for user %s",
                user_id,
            )
            habits = []

        try:
            daily_load = training_load_service.get_daily_load(user_id, target_day=dt)

            recs = recommendation_service.build_recommendations(
                user_id=user_id,
                sleep_score=0,
                recovery_score=0,
                energy_score=0,
                habit_score=0,
                daily_load=daily_load,
                target_date=dt,
            )
        except Exception:
            current_app.logger.exception(
                "Error while building recommendations (fallback) for user %s",
                user_id,
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

        from web.app.models.training_session import TrainingSession

        sessions = (
            TrainingSession.query.filter(
                TrainingSession.user_id == user_id,
                TrainingSession.started_at >= datetime.combine(dt, datetime.min.time()),
                TrainingSession.started_at <= datetime.combine(dt, datetime.max.time()),
            )
            .order_by(TrainingSession.started_at.asc())
            .all()
        )

        training_exercises = []

        training_load = training_load_service.get_daily_load(user_id, target_date=dt)

        training_sessions = len(sessions)

        for session in sessions:
            for exercise in session.exercises:
                training_exercises.append(
                    {
                        "session_id": session.id,
                        "exercise_id": (exercise.exercise_id),
                        "sets": (
                            exercise.sets_done
                            if exercise.sets_done is not None
                            else exercise.sets_planned
                        ),
                        "reps": (
                            exercise.reps_done
                            if exercise.reps_done is not None
                            else exercise.reps_planned
                        ),
                        "load": (
                            exercise.load_done
                            if exercise.load_done is not None
                            else exercise.load_planned
                        ),
                        "rpe": exercise.rpe,
                    }
                )

        has_any = bool(sleep_entry is not None or habits or recs or training_exercises)

        return (
            jsonify(
                {
                    "date": raw_date,
                    "has_data": has_any,
                    "recovery": {
                        "score": None,
                        "status": None,
                        "energy_score": None,
                    },
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
                            getattr(sleep_entry, "sleep_start", None)
                            if sleep_entry
                            else None
                        ),
                        "wake_time": (
                            getattr(sleep_entry, "sleep_end", None)
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
                        "completed": len(
                            [habit for habit in habits if habit.get("completed")]
                        ),
                        "total": len(habits),
                        "score": None,
                        "items": habits,
                    },
                    "recommendations": {
                        "total": len(recs),
                        "items": recs,
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
                    "recovery": {
                        "score": None,
                        "status": None,
                        "energy_score": None,
                    },
                    "sleep": {
                        "duration_minutes": None,
                        "quality_score": None,
                        "bedtime": None,
                        "wake_time": None,
                    },
                    "training": {
                        "load": None,
                        "sessions": 0,
                        "exercises": [],
                    },
                    "habits": {
                        "completed": 0,
                        "total": 0,
                        "score": None,
                        "items": [],
                    },
                    "recommendations": {
                        "total": 0,
                        "items": [],
                    },
                }
            ),
            200,
        )
