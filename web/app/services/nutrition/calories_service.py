from web.app import db
from web.app.models.nutrition.user_goals import UserGoals

ACTIVITY_FACTORS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}


GOAL_ADJUSTMENTS = {
    "lose": -400,
    "lose_fat": -400,
    "fat_loss": -400,
    "cut": -400,
    "maintenance": 0,
    "maintain": 0,
    "recomposition": 0,
    "strength": 0,
    "gain": 250,
    "gain_muscle": 250,
    "muscle_gain": 250,
    "bulk": 300,
}


DEFAULT_ACTIVITY_FACTOR = 1.55


def get_profile(user):
    if not user:
        return None

    return getattr(user, "profile", None)


def get_weight(user):
    profile = get_profile(user)

    if profile and profile.weight is not None:
        return profile.weight

    return getattr(user, "weight", None)


def get_height(user):
    profile = get_profile(user)

    if profile and profile.height is not None:
        return profile.height

    return getattr(user, "height", None)


def get_age(user):
    profile = get_profile(user)

    if profile and profile.age is not None:
        return profile.age

    return getattr(user, "age", None)


def get_gender(user):
    profile = get_profile(user)

    if profile and profile.gender:
        return profile.gender

    return getattr(user, "sex", None)


def get_activity(user):
    profile = get_profile(user)

    if profile and profile.activity:
        return profile.activity

    return getattr(user, "activity", None)


def get_goal(user):
    profile = get_profile(user)

    if profile and profile.goal:
        return profile.goal

    return getattr(user, "goal", None)


def get_activity_factor(activity):
    if activity is None:
        return DEFAULT_ACTIVITY_FACTOR

    try:
        return float(activity)
    except (TypeError, ValueError):
        return ACTIVITY_FACTORS.get(
            str(activity).lower(),
            DEFAULT_ACTIVITY_FACTOR,
        )


def calculate_bmr(user):
    weight = get_weight(user)
    height = get_height(user)
    age = get_age(user)
    gender = get_gender(user)

    if not all(
        [
            weight,
            height,
            age,
        ]
    ):
        return None

    if gender == "male":
        return 10 * weight + 6.25 * height - 5 * age + 5

    if gender == "female":
        return 10 * weight + 6.25 * height - 5 * age - 161

    return 10 * weight + 6.25 * height - 5 * age - 78


def calculate_tdee(user):
    bmr = calculate_bmr(user)

    if bmr is None:
        return None

    activity = get_activity(user)
    activity_factor = get_activity_factor(activity)

    return bmr * activity_factor


def calculate_calories(user):
    tdee = calculate_tdee(user)

    if tdee is None:
        return None

    goal = get_goal(user)

    adjustment = GOAL_ADJUSTMENTS.get(
        goal,
        0,
    )

    return round(tdee + adjustment)


def calculate_macros(user, calories):
    weight = get_weight(user)

    if not weight or not calories:
        return None

    protein = weight * 1.8
    fats = weight * 0.9

    protein_calories = protein * 4
    fat_calories = fats * 9

    carbs_calories = calories - protein_calories - fat_calories

    carbs = max(
        carbs_calories / 4,
        0,
    )

    return {
        "protein": round(protein, 1),
        "fat": round(fats, 1),
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

    goals = UserGoals.query.filter_by(user_id=user.id).first()

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
