from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from myapp.app.services.injury_service import InjuryService

injury_api = Blueprint("injury_api", __name__, url_prefix="/api/injuries")


@injury_api.get("/")
def list_injuries():
    return jsonify(InjuryService.list_injuries())


@injury_api.post("/user")
@login_required
def set_user_injuries():
    data = request.get_json() or {}
    InjuryService.set_user_injuries(current_user, data.get("injuries", []))
    return jsonify({"status": "ok"})
