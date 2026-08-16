from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from myapp.app.services.onboarding_service import OnboardingService

onboarding_api = Blueprint(
    "onboarding_api",
    __name__,
    url_prefix="/api/onboarding"
)


@onboarding_api.post("/profile")
@login_required
def save_profile():
    data = request.get_json() or {}

    profile = OnboardingService.save_profile(
        user=current_user,
        training_location=data.get("training_location"),
        wants_nutrition=data.get("wants_nutrition"),
        wants_recovery=data.get("wants_recovery")
    )

    return jsonify({
        "training_location": profile.training_location,
        "wants_nutrition": profile.wants_nutrition,
        "wants_recovery": profile.wants_recovery
    })


@onboarding_api.post("/goals")
@login_required
def save_goals():
    data = request.get_json() or {}

    goals = OnboardingService.save_goals(
        user=current_user,
        primary_goal=data.get("primary_goal"),
        focus_upper=data.get("focus_upper"),
        focus_lower=data.get("focus_lower"),
        focus_core=data.get("focus_core")
    )

    return jsonify({
        "primary_goal": goals.primary_goal,
        "focus_upper": goals.focus_upper,
        "focus_lower": goals.focus_lower,
        "focus_core": goals.focus_core
    })


@onboarding_api.post("/injuries")
@login_required
def save_injuries():
    data = request.get_json() or {}
    injuries = data.get("injuries", [])

    OnboardingService.save_injuries(current_user, injuries)

    return jsonify({"status": "ok"})


@onboarding_api.post("/complete")
@login_required
def complete_onboarding():
    OnboardingService.complete_onboarding(current_user)
    return jsonify({"onboarding_completed": True})
