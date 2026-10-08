import json
import os

from web.app import create_app
from backend.app.extensions import db
from backend.app.training.exercises.catalog import load_exercise_catalog

BASE_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "backend",
        "app",
        "training",
        "data",
    )
)


def load_json(path):
    if not os.path.exists(path):
        return []

    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def run_seed():
    app = create_app()

    muscles_path = os.path.join(BASE_DIR, "muscles", "muscles.json")
    equipment_path = os.path.join(BASE_DIR, "equipment", "equipment.json")
    exercises_dir = os.path.join(BASE_DIR, "exercises")

    # Validates every record and raises ExerciseDataError before touching the DB.
    exercises = load_exercise_catalog(exercises_dir, muscles_path, equipment_path)

    with app.app_context():
        from backend.app.training.models.muscle import Muscle
        from backend.app.training.models.equipment import TEEquipment
        from backend.app.training.models.exercise import Exercise

        muscles = load_json(muscles_path)
        equipment = load_json(equipment_path)

        created_muscles = 0
        created_equipment = 0
        created_exercises = 0
        updated_exercises = 0

        for item in muscles:
            slug = item.get("slug")
            name = item.get("name")

            if not slug or not name:
                continue

            muscle = Muscle.query.filter_by(slug=slug).first()

            if not muscle:
                muscle = Muscle(
                    slug=slug,
                    name=name,
                    description=item.get("description"),
                )
                db.session.add(muscle)
                created_muscles += 1

        for item in equipment:
            slug = item.get("slug")
            name = item.get("name")

            if not slug or not name:
                continue

            equipment_item = TEEquipment.query.filter_by(slug=slug).first()

            if not equipment_item:
                equipment_item = TEEquipment(
                    slug=slug,
                    name=name,
                    description=item.get("description"),
                )
                equipment_item.set_tags(item.get("tags", []))
                db.session.add(equipment_item)
                created_equipment += 1

        db.session.flush()

        for item in exercises:
            slug = item["slug"]
            fields = {
                "name": item["name"],
                "description": item.get("description"),
                "difficulty": item["difficulty"],
                "location": item.get("location", "any"),
                "movement_pattern": item["movement_pattern"],
                "risk_level": item["risk_level"],
                "muscles_primary": item["muscles_primary"],
                "muscles_secondary": item["muscles_secondary"],
                "equipment": item["equipment"],
                "max_additional_load_kg": item.get("max_additional_load_kg"),
                "muscle_load_profile": item["muscle_load_profile"],
                "measurement_type": item["measurement_type"],
                "load_type": item["load_type"],
                "bodyweight_ratio": item.get("bodyweight_ratio"),
                "prescription": item["prescription"],
            }

            exercise = Exercise.query.filter_by(slug=slug).first()

            if not exercise:
                db.session.add(Exercise(slug=slug, **fields))
                created_exercises += 1
            else:
                for field, value in fields.items():
                    setattr(exercise, field, value)
                updated_exercises += 1

        db.session.commit()

        print(
            f"Seed complete: "
            f"{created_muscles} muscles created, "
            f"{created_equipment} equipment items created, "
            f"{created_exercises} exercises created, "
            f"{updated_exercises} exercises updated."
        )


if __name__ == "__main__":
    run_seed()
