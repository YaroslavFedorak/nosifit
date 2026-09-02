from dataclasses import dataclass

from web.app.training_engine.models.performance_state import (
    PerformanceState,
)

from .constants import MIN_REFERENCE_LOAD
from .parsing import clamp


@dataclass
class UserCapacity:
    age: int
    sex: str
    weight: float
    height: float
    bmi: float
    ffmi: float
    bmr: float
    strength_index: float
    capacity: float


def bmi(weight, height):
    if weight <= 0 or height <= 0:
        return 22.0

    height_m = height / 100.0

    return weight / (height_m**2)


def body_fat(weight, height, age, sex):
    body_mass_index = bmi(weight, height)

    if sex == "female":
        value = 1.20 * body_mass_index + 0.23 * age - 5.4
    else:
        value = 1.20 * body_mass_index + 0.23 * age - 16.2

    return clamp(value, 4.0, 50.0)


def ffmi(weight, height, age, sex):
    if height <= 0:
        return 18.0

    fat_percentage = body_fat(
        weight,
        height,
        age,
        sex,
    )

    lean_mass = weight * (1.0 - fat_percentage / 100.0)
    height_m = height / 100.0

    value = lean_mass / (height_m**2)
    value += 6.1 * (1.8 - height_m)

    return float(value)


def bmr(weight, height, age, sex):
    if sex == "female":
        return 10 * weight + 6.25 * height - 5 * age - 161

    return 10 * weight + 6.25 * height - 5 * age + 5


def estimated_strength(
    pushups,
    squats,
    situps,
    plank_sec=0,
):
    pushups_score = clamp(
        float(pushups) / 60.0,
        0.0,
        1.0,
    )

    squats_score = clamp(
        float(squats) / 80.0,
        0.0,
        1.0,
    )

    situps_score = clamp(
        float(situps) / 80.0,
        0.0,
        1.0,
    )

    plank_score = clamp(
        float(plank_sec) / 180.0,
        0.0,
        1.0,
    )

    return (
        pushups_score * 0.35
        + squats_score * 0.30
        + situps_score * 0.20
        + plank_score * 0.15
    )


def normalize_level(user):
    raw = (
        getattr(user, "level", None)
        or getattr(user, "experience", None)
        or "intermediate"
    )

    value = str(raw).strip().lower()

    mapping = {
        "початківець": "beginner",
        "початковий": "beginner",
        "beginner": "beginner",
        "novice": "beginner",
        "середній": "intermediate",
        "intermediate": "intermediate",
        "досвідчений": "advanced",
        "просунутий": "advanced",
        "advanced": "advanced",
        "елітний": "elite",
        "elite": "elite",
    }

    return mapping.get(value, "intermediate")


def minimum_reference_load(user):
    level = normalize_level(user)

    return MIN_REFERENCE_LOAD.get(
        level,
        MIN_REFERENCE_LOAD["intermediate"],
    )


def build_capacity(user):
    age = getattr(user, "age", None) or 25
    sex = (getattr(user, "sex", None) or "male").lower()

    weight = getattr(user, "weight", None) or 70.0
    height = getattr(user, "height", None) or 175.0

    weight = float(weight)
    height = float(height)
    age = int(age)

    body_mass_index = bmi(
        weight,
        height,
    )

    fat_free_mass_index = ffmi(
        weight,
        height,
        age,
        sex,
    )

    basal_metabolic_rate = bmr(
        weight,
        height,
        age,
        sex,
    )

    performance = None

    states = getattr(
        user,
        "performance_states",
        None,
    )

    if states is not None:
        performance = states.order_by(PerformanceState.created_at.desc()).first()

    pushups = (
        getattr(
            performance,
            "pushups",
            0,
        )
        or 0
    )

    squats = (
        getattr(
            performance,
            "squats",
            0,
        )
        or 0
    )

    situps = (
        getattr(
            performance,
            "situps",
            0,
        )
        or 0
    )

    plank_sec = (
        getattr(
            performance,
            "plank_sec",
            0,
        )
        or 0
    )

    strength_index = estimated_strength(
        pushups,
        squats,
        situps,
        plank_sec,
    )

    if age <= 35:
        age_factor = 1.00
    elif age <= 50:
        age_factor = 0.96
    elif age <= 65:
        age_factor = 0.91
    else:
        age_factor = 0.86

    if body_mass_index < 18.5:
        bmi_factor = 0.95
    elif body_mass_index <= 25:
        bmi_factor = 1.00
    elif body_mass_index <= 30:
        bmi_factor = 0.98
    else:
        bmi_factor = 0.95

    ffmi_factor = clamp(
        fat_free_mass_index / 20.0,
        0.90,
        1.10,
    )

    strength_factor = 0.95 + strength_index * 0.15

    experience = (getattr(user, "experience", None) or normalize_level(user)).lower()

    experience_factor = {
        "beginner": 0.92,
        "novice": 0.96,
        "intermediate": 1.00,
        "advanced": 1.05,
        "elite": 1.08,
        "початківець": 0.92,
        "середній": 1.00,
        "досвідчений": 1.05,
        "просунутий": 1.05,
        "елітний": 1.08,
    }.get(
        experience,
        1.00,
    )

    activity = (getattr(user, "activity", None) or "moderate").lower()

    activity_factor = {
        "sedentary": 0.94,
        "low": 0.97,
        "moderate": 1.00,
        "high": 1.04,
        "very_high": 1.07,
    }.get(
        activity,
        1.00,
    )

    frequency = (
        getattr(
            user,
            "workouts_per_week",
            None,
        )
        or 3
    )

    if frequency <= 2:
        frequency_factor = 0.96
    elif frequency <= 4:
        frequency_factor = 1.00
    elif frequency <= 6:
        frequency_factor = 1.03
    else:
        frequency_factor = 1.06

    goal = (getattr(user, "goal", None) or "maintenance").lower()

    goal_factor = {
        "fat_loss": 0.98,
        "maintenance": 1.00,
        "muscle_gain": 1.02,
        "strength": 1.04,
        "performance": 1.05,
    }.get(
        goal,
        1.00,
    )

    capacity = (
        age_factor
        * bmi_factor
        * ffmi_factor
        * strength_factor
        * experience_factor
        * activity_factor
        * frequency_factor
        * goal_factor
    )

    capacity = clamp(
        capacity,
        0.85,
        1.15,
    )

    return UserCapacity(
        age=age,
        sex=sex,
        weight=weight,
        height=height,
        bmi=float(body_mass_index),
        ffmi=float(fat_free_mass_index),
        bmr=float(basal_metabolic_rate),
        strength_index=float(strength_index),
        capacity=float(capacity),
    )


def reference_capacity(user):
    capacity = build_capacity(user)
    minimum = minimum_reference_load(user)

    return max(
        minimum,
        minimum * capacity.capacity,
    )
