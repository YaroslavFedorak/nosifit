from datetime import datetime
from web.app import db


class UserEquipment(db.Model):
    __tablename__ = "te_user_equipment"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    equipment_id = db.Column(db.Integer, nullable=False, index=True)
    available = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "equipment_id": self.equipment_id,
            "available": self.available,
            "notes": self.notes,
        }

    def __repr__(self):
        return f"<UserEquipment user_id={self.user_id} equipment_id={self.equipment_id} available={self.available}>"
