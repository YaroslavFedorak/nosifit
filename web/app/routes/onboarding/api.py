from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from backend.app.services.onboarding_service import OnboardingService
from backend.app.services.injury_service import clean_injury_ids
from backend.app.utils.validation import ValidationError, bounded_number, clean_choice

onboarding_api = Blueprint("onboarding_api", __name__, url_prefix="/api/onboarding")


def _body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _invalid():
    return jsonify({"error": "invalid_input"}), 400


@onboarding_api.post("/profile")
@login_required
def save_profile():
    data = _body()

    try:
        training_location = clean_choice("training_location", data.get("training_location")) or "home"
    except ValidationError:
        return _invalid()

    profile = OnboardingService.save_profile(
        user=current_user,
        training_location=training_location,
        wants_nutrition=data.get("wants_nutrition") is True,
        wants_recovery=data.get("wants_recovery") is True,
    )

    return jsonify(
        {
            "training_location": profile.training_location,
            "wants_nutrition": profile.wants_nutrition,
            "wants_recovery": profile.wants_recovery,
        }
    )


@onboarding_api.post("/goals")
@login_required
def save_goals():
    data = _body()

    try:
        primary_goal = clean_choice("goal", data.get("primary_goal"))
        if not primary_goal:
            raise ValidationError("primary_goal is required")
        focus = {
            key: bounded_number(data.get(key), 0, 10, integer=True)
            for key in ("focus_upper", "focus_lower", "focus_core")
        }
    except ValidationError:
        return _invalid()

    goals = OnboardingService.save_goals(
        user=current_user,
        primary_goal=primary_goal,
        **focus,
    )

    return jsonify(
        {
            "primary_goal": goals.primary_goal,
            "focus_upper": goals.focus_upper,
            "focus_lower": goals.focus_lower,
            "focus_core": goals.focus_core,
        }
    )


@onboarding_api.post("/injuries")
@login_required
def save_injuries():
    try:
        injuries = clean_injury_ids(_body().get("injuries", []))
    except ValidationError:
        return _invalid()

    OnboardingService.save_injuries(current_user, injuries)

    return jsonify({"status": "ok"})


@onboarding_api.post("/complete")
@login_required
def complete_onboarding():
    OnboardingService.complete_onboarding(current_user)
    return jsonify({"onboarding_completed": True})
