from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from backend.app.dashboard.training.service import TrainingDashboardService
from backend.app.services.training.validation import (
    clean_exercise_id,
    clean_fatigue,
    clean_set_data,
)
from backend.app.utils.validation import ValidationError

training_dashboard_api_bp = Blueprint(
    "training_dashboard_api",
    __name__,
    url_prefix="/api/dashboard/training",
)


@training_dashboard_api_bp.get("")
@login_required
def today():
    data = TrainingDashboardService.get_today(current_user.id)

    return jsonify(data)


@training_dashboard_api_bp.get("/session/<int:session_id>")
@login_required
def session(session_id):
    data = TrainingDashboardService.get_session(
        current_user.id,
        session_id,
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

    try:
        fatigue_before = clean_fatigue(payload.get("fatigue_before"))
    except ValidationError:
        return jsonify({"error": "invalid_fatigue"}), 400

    session_data = TrainingDashboardService.start(
        current_user.id,
        fatigue_before=fatigue_before,
    )

    if session_data is None:
        return (
            jsonify(
                {
                    "error": "user_not_found",
                }
            ),
            404,
        )

    return (
        jsonify(
            {
                "session": session_data,
            }
        ),
        201,
    )


@training_dashboard_api_bp.post("/session/<int:session_id>/exercise")
@login_required
def add_exercise(session_id):
    payload = request.get_json(silent=True) or {}

    exercise_id = payload.get("exercise_id")

    if isinstance(exercise_id, bool) or not isinstance(exercise_id, (str, int)) or not exercise_id:
        return (
            jsonify(
                {
                    "error": "exercise_id_required",
                }
            ),
            400,
        )

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

    try:
        exercise_id = clean_exercise_id(exercise_id)
        set_data = clean_set_data(payload)
    except ValidationError:
        return jsonify({"error": "invalid_exercise_data"}), 400

    data = TrainingDashboardService.update_exercise(
        current_user.id,
        session_id,
        exercise_id,
        set_data,
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

    try:
        fatigue_after = clean_fatigue(payload.get("fatigue_after"))
    except ValidationError:
        return jsonify({"error": "invalid_fatigue"}), 400

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

