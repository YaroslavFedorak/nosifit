from datetime import datetime
from web.app import db
import json


class TEEquipment(db.Model):
    __tablename__ = "te_equipment"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    tags = db.Column(db.Text, nullable=True)
    description = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def set_tags(self, tags_list):
        try:
            self.tags = json.dumps(tags_list)
        except Exception:
            self.tags = "[]"

    def get_tags(self):
        try:
            return json.loads(self.tags) if self.tags else []
        except Exception:
            return []

    def to_dict(self):
        return {
            "id": self.id,
            "slug": self.slug,
            "name": self.name,
            "tags": self.get_tags(),
            "description": self.description,
        }

    def __repr__(self):
        return f"<TEEquipment slug={self.slug} name={self.name}>"
