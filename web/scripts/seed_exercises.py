import json
import os

from web.app import create_app
from backend.app.extensions import db

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


def load_all_from_dir(path):
    items = []

    if not os.path.exists(path):
        return items

    for filename in os.listdir(path):
        if not filename.endswith(".json"):
            continue

        file_path = os.path.join(path, filename)

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            if isinstance(data, list):
                items.extend(data)
        except Exception:
            continue

    return items


def run_seed():
    app = create_app()

    muscles_path = os.path.join(BASE_DIR, "muscles", "muscles.json")
    equipment_path = os.path.join(BASE_DIR, "equipment", "equipment.json")
    exercises_dir = os.path.join(BASE_DIR, "exercises")

    with app.app_context():
        from backend.app.training.models.muscle import Muscle
        from backend.app.training.models.equipment import TEEquipment
        from backend.app.training.models.exercise import Exercise

        muscles = load_json(muscles_path)
        equipment = load_json(equipment_path)
        exercises = load_all_from_dir(exercises_dir)

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
            name = item.get("name")
            slug = item.get("slug")

            if not name:
                continue

            if not slug:
                slug = name.lower().replace(" ", "-")

            exercise = Exercise.query.filter_by(slug=slug).first()

            if not exercise:
                exercise = Exercise(
                    name=name,
                    slug=slug,
                    description=item.get("description"),
                    difficulty=item.get("difficulty", 1),
                    location=item.get("location", "any"),
                    movement_pattern=item.get("movement_pattern"),
                    risk_level=item.get("risk_level", 1),
                    muscles_primary=item.get("muscles_primary", []),
                    muscles_secondary=item.get("muscles_secondary", []),
                    equipment=item.get("equipment", []),
                    max_additional_load_kg=item.get("max_additional_load_kg"),
                    muscle_load_profile=item.get("muscle_load_profile"),
                )
                db.session.add(exercise)
                created_exercises += 1
            else:
                exercise.name = name
                exercise.description = item.get("description")
                exercise.difficulty = item.get("difficulty", 1)
                exercise.location = item.get("location", "any")
                exercise.movement_pattern = item.get("movement_pattern")
                exercise.risk_level = item.get("risk_level", 1)
                exercise.muscles_primary = item.get("muscles_primary", [])
                exercise.muscles_secondary = item.get("muscles_secondary", [])
                exercise.equipment = item.get("equipment", [])
                exercise.max_additional_load_kg = item.get("max_additional_load_kg")
                exercise.muscle_load_profile = item.get("muscle_load_profile")
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
