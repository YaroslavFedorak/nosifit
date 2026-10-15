from backend.app.extensions import db
from backend.app.models.nutrition.user_weight import UserWeight
from backend.app.models.user_profile import UserProfile
from backend.app.utils import clock
from backend.app.utils.validation import PROFILE_RANGES

# WHO adult BMI classes (kg/m2). They apply from 18 years; for children and
# adolescents BMI is read against age- and sex-specific growth charts, which
# are not available here, so no class is given below 18 or without an age.
ADULT_MIN_AGE = 18
BMI_CLASSES = (
    (18.5, "underweight"),
    (25.0, "normal"),
    (30.0, "overweight"),
)


def bmi_category(bmi, age):
    """WHO adult class of a BMI, or ``None`` when it should not be classified."""
    if bmi is None or age is None or age < ADULT_MIN_AGE:
        return None
    for upper, name in BMI_CLASSES:
        if bmi < upper:
            return name
    return "obese"


def calculate_bmi(weight, height_cm):
    """BMI rounded to 0.1, or ``None`` when weight or height is missing or implausible."""
    try:
        weight = float(weight)
        height_cm = float(height_cm)
    except (TypeError, ValueError):
        return None
    w_low, w_high, _ = PROFILE_RANGES["weight"]
    h_low, h_high, _ = PROFILE_RANGES["height"]
    if not (w_low <= weight <= w_high and h_low <= height_cm <= h_high):
        return None
    return round(weight / (height_cm / 100) ** 2, 1)


def get_current_weight(user_id):
    entry = UserWeight.query.filter_by(
        user_id=user_id,
        date=clock.today(),
    ).first()

    if entry is not None:
        return entry.weight

    profile = UserProfile.query.filter_by(
        user_id=user_id,
    ).first()

    if profile is not None:
        return profile.weight

    return None


def get_weight_data(user_id):
    profile = UserProfile.query.filter_by(
        user_id=user_id,
    ).first()

    weight = get_current_weight(
        user_id,
    )

    bmi = None
    category = None

    if profile is not None:
        bmi = calculate_bmi(weight, profile.height)
        category = bmi_category(bmi, profile.age)

    return {
        "weight": weight,
        "bmi": bmi,
        # None = not classified (under 18 or age unknown): a number only.
        "bmi_category": category,
        "bmi_classified": category is not None,
    }


def update_user_weight(user, weight):
    today = clock.today()

    entry = UserWeight.query.filter_by(
        user_id=user.id,
        date=today,
    ).first()

    if entry is None:
        entry = UserWeight(
            user_id=user.id,
            date=today,
            weight=weight,
        )

        db.session.add(entry)

    else:
        entry.weight = weight

    profile = user.profile

    if profile is None:
        profile = UserProfile(
            user_id=user.id,
            training_location="home",
        )

        db.session.add(profile)

    profile.weight = weight

    db.session.commit()

    return entry

