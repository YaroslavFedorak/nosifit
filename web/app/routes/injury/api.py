from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from backend.app.services.injury_service import InjuryService, clean_injury_ids
from backend.app.utils.validation import ValidationError

injury_api = Blueprint("injury_api", __name__, url_prefix="/api/injuries")


@injury_api.get("/")
def list_injuries():
    return jsonify(InjuryService.list_injuries())


@injury_api.post("/user")
@login_required
def set_user_injuries():
    data = request.get_json(silent=True)
    data = data if isinstance(data, dict) else {}
    try:
        injuries = clean_injury_ids(data.get("injuries", []))
    except ValidationError:
        return jsonify({"error": "invalid_input"}), 400
    InjuryService.set_user_injuries(current_user, injuries)
    return jsonify({"status": "ok"})

