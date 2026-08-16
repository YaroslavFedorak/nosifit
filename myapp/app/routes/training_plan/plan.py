from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user

from myapp.app.training_engine.models.training_plan import TrainingPlan

plan_bp = Blueprint("plan", __name__, url_prefix="/plan")


def _active_plan(user):
    return (
        TrainingPlan.query.filter_by(user_id=user.id, is_active=True)
        .order_by(TrainingPlan.id.desc())
        .first()
    )


@plan_bp.get("/view")
@login_required
def view_plan():
    plan = _active_plan(current_user)

    if not plan:
        return render_template(
            "app/plan.html",
            plan={"id": None, "name": "No active plan", "days": {}},
            user=current_user,
        )

    return render_template("app/plan.html", plan=plan.to_dict(), user=current_user)


@plan_bp.get("/json")
@login_required
def view_plan_json():
    plan = _active_plan(current_user)

    if not plan:
        return jsonify(
            {
                "id": None,
                "user_id": current_user.id,
                "name": "No active plan",
                "is_active": False,
                "days": {},
                "created_at": None,
                "updated_at": None,
            }
        )

    return jsonify(plan.to_dict())
