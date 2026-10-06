from backend.app.extensions import db
from backend.app.models.injury import Injury
from backend.app.models.user_injury import UserInjury
from backend.app.utils.validation import ValidationError

MAX_USER_INJURIES = 50


def clean_injury_ids(value):
    """Unique ids of existing injuries; raises ValidationError otherwise."""
    if not isinstance(value, list) or len(value) > MAX_USER_INJURIES:
        raise ValidationError("injuries must be a list")
    ids = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int):
            raise ValidationError("injury ids must be integers")
        if item not in ids:
            ids.append(item)
    if ids and Injury.query.filter(Injury.id.in_(ids)).count() != len(ids):
        raise ValidationError("unknown injury")
    return ids


class InjuryService:

    @staticmethod
    def list_injuries():
        injuries = Injury.query.all()
        return [
            {"id": i.id, "name": i.name, "description": i.description} for i in injuries
        ]

    @staticmethod
    def set_user_injuries(user, injury_ids):
        UserInjury.query.filter_by(user_id=user.id).delete()

        for injury_id in injury_ids:
            db.session.add(UserInjury(user_id=user.id, injury_id=injury_id))

        db.session.commit()

