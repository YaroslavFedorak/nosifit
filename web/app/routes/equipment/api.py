from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from backend.app.services.equipment_service import EquipmentService

equipment_api = Blueprint("equipment_api", __name__, url_prefix="/api/user/equipment")


@equipment_api.get("/")
@login_required
def get_equipment():
    items = EquipmentService.get_user_equipment(current_user)
    return jsonify(items)


def _equipment_id():
    data = request.get_json(silent=True)
    value = data.get("equipment_id") if isinstance(data, dict) else None
    if isinstance(value, bool):
        return None
    if isinstance(value, str) and value.strip().isdigit() and len(value) < 10:
        value = int(value)
    return value if isinstance(value, int) and 0 < value < 2**31 else None


@equipment_api.post("/add")
@login_required
def add_equipment():
    equipment_id = _equipment_id()
    if equipment_id is None or not EquipmentService.add_equipment(current_user, equipment_id):
        return jsonify({"error": "Equipment not found"}), 404
    return jsonify({"status": "added"})


@equipment_api.post("/remove")
@login_required
def remove_equipment():
    equipment_id = _equipment_id()
    if equipment_id is None:
        return jsonify({"error": "invalid_input"}), 400
    EquipmentService.remove_equipment(current_user, equipment_id)
    return jsonify({"status": "removed"})

