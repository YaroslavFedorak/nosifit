from datetime import date

from web.app import db
from web.app.models.nutrition.user_weight import UserWeight
from web.app.models.user_profile import UserProfile


def get_current_weight(user_id):
    entry = UserWeight.query.filter_by(
        user_id=user_id,
        date=date.today(),
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

    if profile is not None and profile.height and weight and profile.height > 0:
        height_m = profile.height / 100

        bmi = round(
            weight / (height_m**2),
            1,
        )

    return {
        "weight": weight,
        "bmi": bmi,
    }


def update_user_weight(user, weight):
    today = date.today()

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
