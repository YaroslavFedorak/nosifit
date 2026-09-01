from datetime import date

from myapp.app import db
from myapp.app.models.nutrition.user_weight import UserWeight
from myapp.app.models.user_profile import UserProfile


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
