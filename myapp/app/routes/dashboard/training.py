from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from myapp.app.dashboard.training.service import TrainingDashboardService

training_dashboard_api_bp = Blueprint(
    "training_dashboard_api",
    __name__,
    url_prefix="/api/dashboard/training",
)


@training_dashboard_api_bp.get("")
@login_required
def today():
    return jsonify(TrainingDashboardService.get_today(current_user.id))


@training_dashboard_api_bp.get("/session/<int:session_id>")
@login_required
def session(session_id):
    data = TrainingDashboardService.get_session(
        current_user.id,
        session_id,
    )

    if data is None:
        return jsonify({"error": "session_not_found"}), 404

    return jsonify(data)


@training_dashboard_api_bp.get("/exercises")
@login_required
def exercises():
    search = request.args.get("search")
    movement_pattern = request.args.get("movement_pattern")
    difficulty = request.args.get("difficulty")

    data = TrainingDashboardService.get_exercises(
        search=search,
        movement_pattern=movement_pattern,
        difficulty=difficulty,
    )

    return jsonify(
        {
            "exercises": data,
        }
    )


@training_dashboard_api_bp.post("/session")
@login_required
def start_session():
    payload = request.get_json(silent=True) or {}

    fatigue_before = payload.get("fatigue_before")

    session = TrainingDashboardService.start(
        current_user.id,
        fatigue_before=fatigue_before,
    )

    if session is None:
        return jsonify({"error": "user_not_found"}), 404

    return (
        jsonify(
            {
                "session": session,
            }
        ),
        201,
    )


@training_dashboard_api_bp.post("/session/<int:session_id>/exercise")
@login_required
def add_exercise(session_id):
    payload = request.get_json(silent=True) or {}

    exercise_id = payload.get("exercise_id")

    if not exercise_id:
        return jsonify({"error": "exercise_id_required"}), 400

    data = TrainingDashboardService.add_exercise(
        current_user.id,
        session_id,
        exercise_id,
    )

    if data is None:
        return (
            jsonify(
                {
                    "error": "session_or_exercise_not_found",
                }
            ),
            404,
        )

    return (
        jsonify(
            {
                "exercise": data,
            }
        ),
        201,
    )


@training_dashboard_api_bp.patch("/session/<int:session_id>/exercise/<exercise_id>")
@login_required
def update_exercise(session_id, exercise_id):
    payload = request.get_json(silent=True) or {}

    data = TrainingDashboardService.update_exercise(
        current_user.id,
        session_id,
        exercise_id,
        payload,
    )

    if data is None:
        return (
            jsonify(
                {
                    "error": "session_or_exercise_not_found",
                }
            ),
            404,
        )

    return jsonify(
        {
            "exercise": data,
        }
    )


@training_dashboard_api_bp.post("/session/<int:session_id>/finish")
@login_required
def finish_session(session_id):
    payload = request.get_json(silent=True) or {}

    fatigue_after = payload.get("fatigue_after")

    data = TrainingDashboardService.finish(
        current_user.id,
        session_id,
        fatigue_after=fatigue_after,
    )

    if data is None:
        return (
            jsonify(
                {
                    "error": "session_not_found",
                }
            ),
            404,
        )

    return jsonify(
        {
            "session": data,
        }
    )
