from backend.app.extensions import db
from backend.app.models.nutrition.user_goals import UserGoals

# Two forms store the activity level in two ways. The profile editor saves a
# label (sedentary, light, moderate, active); the registration and
# complete-profile forms save the factor itself ("1.2", "1.375", "1.55",
# "1.725", "1.9"). Both are valid and mean the same: ``activity_level``
# turns either into one canonical label, and every formula (targets, water)
# goes through it. ``very_active`` is only ever stored as "1.9": the label
# itself is 11 characters, and the ``activity`` column holds 10.
ACTIVITY_FACTORS = {
    "sedentary": 1.20,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.90,
}

DEFAULT_ACTIVITY_FACTOR = 1.55

GOAL_ALIASES = {
    # The registration form offers "performance"; such a user is fed at
    # maintenance (stated here rather than left to the silent default).
    "performance": "maintenance",
    "lose": "cut",
    "lose_fat": "cut",
    "fat_loss": "cut",
    "cut": "cut",
    "maintenance": "maintenance",
    "maintain": "maintenance",
    "recomposition": "recomp",
    "recomp": "recomp",
    "strength": "strength",
    "lean_gain": "lean_gain",
    "gain": "gain",
    "gain_muscle": "gain",
    "muscle_gain": "gain",
    "bulk": "gain",
}

DEFAULT_GOAL = "maintenance"

GOAL_CALORIE_ADJUSTMENTS = {
    "cut": -0.15,
    "maintenance": 0.00,
    "recomp": 0.00,
    "strength": 0.05,
    "lean_gain": 0.08,
    "gain": 0.10,
}

PROTEIN_FACTORS = {
    "cut": 2.0,
    "maintenance": 1.6,
    "recomp": 1.8,
    "strength": 1.8,
    "lean_gain": 1.8,
    "gain": 1.6,
}

DEFAULT_PROTEIN_FACTOR = 1.6

# Acceptable Macronutrient Distribution Ranges (US National Academies, 2005):
# protein 10-35%, fat 20-35% and carbohydrate 45-65% of energy. The g/kg
# protein factors use total body weight, so for a heavy person they can ask
# for more than the range allows; protein is then capped at its upper bound.
MAX_PROTEIN_CALORIE_RATIO = 0.35

MIN_FAT_CALORIE_RATIO = 0.20
MAX_FAT_CALORIE_RATIO = 0.35
DEFAULT_FAT_CALORIE_RATIO = 0.28

MIN_CARB_CALORIE_RATIO = 0.45
MAX_CARB_CALORIE_RATIO = 0.65

MIN_CALORIES_MALE = 1500
MIN_CALORIES_FEMALE = 1200
MIN_CALORIES_UNKNOWN = 1350

MAX_REASONABLE_CALORIES = 6000

MIN_AGE = 15
MAX_AGE = 100
MIN_WEIGHT_KG = 30.0
MAX_WEIGHT_KG = 300.0
MIN_HEIGHT_CM = 120.0
MAX_HEIGHT_CM = 230.0


def get_profile(user):
    if not user:
        return None

    return getattr(user, "profile", None)


def get_weight(user):
    profile = get_profile(user)

    if profile and profile.weight is not None:
        return float(profile.weight)

    weight = getattr(user, "weight", None)

    if weight is not None:
        return float(weight)

    return None


def get_height(user):
    profile = get_profile(user)

    if profile and profile.height is not None:
        return float(profile.height)

    height = getattr(user, "height", None)

    if height is not None:
        return float(height)

    return None


def get_age(user):
    profile = get_profile(user)

    if profile and profile.age is not None:
        return int(profile.age)

    age = getattr(user, "age", None)

    if age is not None:
        return int(age)

    return None


def get_gender(user):
    profile = get_profile(user)

    if profile and profile.gender:
        return str(profile.gender).strip().lower()

    gender = getattr(user, "sex", None)

    if gender:
        return str(gender).strip().lower()

    return None


def get_activity(user):
    profile = get_profile(user)

    if profile and profile.activity is not None:
        return profile.activity

    return getattr(user, "activity", None)


def get_goal(user):
    profile = get_profile(user)

    raw_goal = None

    if profile and profile.goal:
        raw_goal = str(profile.goal).strip().lower()
    else:
        goal = getattr(user, "goal", None)

        if goal:
            raw_goal = str(goal).strip().lower()

    if not raw_goal:
        return DEFAULT_GOAL

    return GOAL_ALIASES.get(
        raw_goal,
        DEFAULT_GOAL,
    )


def validate_profile(user):
    weight = get_weight(user)
    height = get_height(user)
    age = get_age(user)

    if weight is None or height is None or age is None:
        return False

    if not MIN_WEIGHT_KG <= weight <= MAX_WEIGHT_KG:
        return False

    if not MIN_HEIGHT_CM <= height <= MAX_HEIGHT_CM:
        return False

    if not MIN_AGE <= age <= MAX_AGE:
        return False

    return True


def activity_level(activity):
    """The canonical level of a stored activity value, or ``None``.

    Accepts a label (any case) or a factor between 1.2 and 1.9 (a number or
    numeric text), which maps to the nearest level.
    """
    if activity is None or isinstance(activity, bool):
        return None

    try:
        factor = float(activity)
    except (TypeError, ValueError):
        label = str(activity).strip().lower()
        return label if label in ACTIVITY_FACTORS else None

    if not 1.20 <= factor <= 1.90:
        return None

    return min(ACTIVITY_FACTORS, key=lambda name: abs(ACTIVITY_FACTORS[name] - factor))


def get_activity_factor(activity):
    if activity is None:
        return DEFAULT_ACTIVITY_FACTOR

    try:
        numeric_activity = float(activity)

        if 1.20 <= numeric_activity <= 1.90:
            return numeric_activity

    except (TypeError, ValueError):
        pass

    normalized_activity = str(activity).strip().lower()

    return ACTIVITY_FACTORS.get(
        normalized_activity,
        DEFAULT_ACTIVITY_FACTOR,
    )


def calculate_bmr(user):
    if not validate_profile(user):
        return None

    weight = get_weight(user)
    height = get_height(user)
    age = get_age(user)
    gender = get_gender(user)

    base = 10 * weight + 6.25 * height - 5 * age

    if gender == "male":
        return base + 5

    if gender == "female":
        return base - 161

    return base - 78


def calculate_tdee(user):
    bmr = calculate_bmr(user)

    if bmr is None:
        return None

    activity_factor = get_activity_factor(get_activity(user))

    return bmr * activity_factor


def get_goal_adjustment(goal):
    return GOAL_CALORIE_ADJUSTMENTS.get(
        goal,
        0.0,
    )


def get_minimum_calories(user):
    gender = get_gender(user)

    if gender == "female":
        return MIN_CALORIES_FEMALE

    if gender == "male":
        return MIN_CALORIES_MALE

    return MIN_CALORIES_UNKNOWN


def calculate_calories(user):
    tdee = calculate_tdee(user)

    if tdee is None:
        return None

    goal = get_goal(user)
    adjustment = get_goal_adjustment(goal)

    calories = tdee * (1 + adjustment)

    calories = max(
        calories,
        get_minimum_calories(user),
    )

    calories = min(
        calories,
        MAX_REASONABLE_CALORIES,
    )

    return round(calories)


def get_protein_factor(goal):
    return PROTEIN_FACTORS.get(
        goal,
        DEFAULT_PROTEIN_FACTOR,
    )


def calculate_protein(user):
    weight = get_weight(user)

    if weight is None:
        return None

    goal = get_goal(user)
    factor = get_protein_factor(goal)

    return weight * factor


def calculate_fat(calories, protein):
    protein_calories = protein * 4

    minimum_fat_calories = calories * MIN_FAT_CALORIE_RATIO

    maximum_fat_calories = calories * MAX_FAT_CALORIE_RATIO

    target_fat_calories = calories * DEFAULT_FAT_CALORIE_RATIO

    available_calories = max(
        calories - protein_calories,
        0,
    )

    fat_calories = min(
        target_fat_calories,
        available_calories,
    )

    fat_calories = max(
        fat_calories,
        min(
            minimum_fat_calories,
            available_calories,
        ),
    )

    fat_calories = min(
        fat_calories,
        maximum_fat_calories,
        available_calories,
    )

    return fat_calories / 9


def calculate_carbs(calories, protein, fat):
    protein_calories = protein * 4
    fat_calories = fat * 9

    remaining_calories = max(
        calories - protein_calories - fat_calories,
        0,
    )

    return remaining_calories / 4


def calculate_macros(user, calories):
    if calories is None:
        return None

    if get_weight(user) is None:
        return None

    protein = calculate_protein(user)

    if protein is None:
        return None

    protein = min(protein, calories * MAX_PROTEIN_CALORIE_RATIO / 4)

    fat = calculate_fat(
        calories,
        protein,
    )

    carbs = calculate_carbs(
        calories,
        protein,
        fat,
    )

    protein_calories = protein * 4
    fat_calories = fat * 9
    carb_calories = carbs * 4

    total_macro_calories = protein_calories + fat_calories + carb_calories

    if total_macro_calories <= 0:
        return None

    carb_ratio = carb_calories / calories

    if carb_ratio < MIN_CARB_CALORIE_RATIO:
        required_carb_calories = calories * MIN_CARB_CALORIE_RATIO

        additional_carb_calories = required_carb_calories - carb_calories

        available_fat_calories = max(
            fat_calories - calories * MIN_FAT_CALORIE_RATIO,
            0,
        )

        shift = min(
            additional_carb_calories,
            available_fat_calories,
        )

        fat_calories -= shift
        carb_calories += shift

    elif carb_ratio > MAX_CARB_CALORIE_RATIO:
        excess_carb_calories = carb_calories - calories * MAX_CARB_CALORIE_RATIO

        available_fat_calories = max(
            calories * MAX_FAT_CALORIE_RATIO - fat_calories,
            0,
        )

        shift = min(
            excess_carb_calories,
            available_fat_calories,
        )

        fat_calories += shift
        carb_calories -= shift

    fat = fat_calories / 9
    carbs = max(carb_calories, 0) / 4

    return {
        "protein": round(protein, 1),
        "fat": round(fat, 1),
        "carbs": round(carbs, 1),
    }


def calculate_nutrition_goals(user):
    calories = calculate_calories(user)

    if calories is None:
        return None

    macros = calculate_macros(
        user,
        calories,
    )

    if macros is None:
        return None

    return {
        "calories": calories,
        "protein": macros["protein"],
        "fat": macros["fat"],
        "carbs": macros["carbs"],
    }


def update_user_nutrition_goals(user):
    calculated = calculate_nutrition_goals(user)

    if calculated is None:
        return None

    goals = UserGoals.query.filter_by(
        user_id=user.id,
    ).first()

    if not goals:
        goals = UserGoals(
            user_id=user.id,
        )

        db.session.add(goals)

    goals.calories_goal = calculated["calories"]
    goals.protein_goal = calculated["protein"]
    goals.fat_goal = calculated["fat"]
    goals.carb_goal = calculated["carbs"]

    db.session.commit()

    return goals

