from datetime import datetime
import uuid
from sqlalchemy.dialects.postgresql import JSONB
from backend.app.extensions import db


class Exercise(db.Model):
    __tablename__ = "te_exercises"

    id = db.Column(db.String(250), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(250), nullable=False, unique=True)
    slug = db.Column(db.String(250), nullable=True)
    description = db.Column(db.Text, nullable=True)
    difficulty = db.Column(db.Integer, default=1)
    location = db.Column(db.String(30), default="any")
    movement_pattern = db.Column(db.String(50), nullable=True)
    risk_level = db.Column(db.Integer, default=1)

    muscles_primary = db.Column(JSONB, default=list)
    muscles_secondary = db.Column(JSONB, default=list)
    equipment = db.Column(JSONB, default=list)

    max_additional_load_kg = db.Column(db.Integer, nullable=True)
    muscle_load_profile = db.Column(JSONB, nullable=True)

    # "reps" or "duration"; see backend/app/training/exercises/catalog.py.
    measurement_type = db.Column(
        db.String(16), nullable=False, default="reps", server_default="reps"
    )
    load_type = db.Column(db.String(16), nullable=True)
    bodyweight_ratio = db.Column(db.Float, nullable=True)
    prescription = db.Column(JSONB, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def to_dict(self):
        return {
            "id": self.id,
            "slug": self.slug,
            "name": self.name,
            "description": self.description,
            "difficulty": self.difficulty,
            "location": self.location,
            "movement_pattern": self.movement_pattern,
            "risk_level": self.risk_level,
            "muscles_primary": self.muscles_primary or [],
            "muscles_secondary": self.muscles_secondary or [],
            "equipment": self.equipment or [],
            "max_additional_load_kg": self.max_additional_load_kg,
            "muscle_load_profile": self.muscle_load_profile,
            "measurement_type": self.measurement_type or "reps",
            "load_type": self.load_type,
            "bodyweight_ratio": self.bodyweight_ratio,
            "prescription": self.prescription,
        }

    def __repr__(self):
        return f"<Exercise id={self.id} name={self.name}>"

