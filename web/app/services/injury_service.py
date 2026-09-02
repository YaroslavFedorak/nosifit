from web.app import db
from web.app.models.injury import Injury
from web.app.models.user_injury import UserInjury


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
