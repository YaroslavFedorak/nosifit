from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from myapp.app.services.equipment_service import EquipmentService

equipment_api = Blueprint("equipment_api", __name__, url_prefix="/api/user/equipment")


@equipment_api.get("/")
@login_required
def get_equipment():
    items = EquipmentService.get_user_equipment(current_user)
    return jsonify(items)


@equipment_api.post("/add")
@login_required
def add_equipment():
    data = request.get_json() or {}
    EquipmentService.add_equipment(current_user, data.get("equipment_id"))
    return jsonify({"status": "added"})


@equipment_api.post("/remove")
@login_required
def remove_equipment():
    data = request.get_json() or {}
    EquipmentService.remove_equipment(current_user, data.get("equipment_id"))
    return jsonify({"status": "removed"})
