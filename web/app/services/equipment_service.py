from web.app import db
from web.app.models.user_equipment import UserEquipment
from web.app.training_engine.models.equipment import TEEquipment


class EquipmentService:

    @staticmethod
    def get_user_equipment(user):
        items = UserEquipment.query.filter_by(user_id=user.id).all()
        eq_ids = [ue.equipment_id for ue in items]
        eq_objects = TEEquipment.query.filter(TEEquipment.id.in_(eq_ids)).all()

        result = []
        for eq in eq_objects:
            result.append(eq.to_dict())

        return result

    @staticmethod
    def add_equipment(user, equipment_id):
        eq = TEEquipment.query.filter_by(id=equipment_id).first()
        if not eq:
            return False

        exists = UserEquipment.query.filter_by(
            user_id=user.id, equipment_id=equipment_id
        ).first()

        if exists:
            return True

        ue = UserEquipment(user_id=user.id, equipment_id=equipment_id, available=True)
        db.session.add(ue)
        db.session.commit()
        return True

    @staticmethod
    def remove_equipment(user, equipment_id):
        UserEquipment.query.filter_by(
            user_id=user.id, equipment_id=equipment_id
        ).delete()

        db.session.commit()
        return True
