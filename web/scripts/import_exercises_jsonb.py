import json
from pathlib import Path

from backend.app.extensions import db
from backend.app.models.user import User
from backend.app.training.models.exercise import Exercise
from backend.app.factory import create_backend_app


BASE_DIR = Path(__file__).resolve().parents[2]
EXERCISES_DIR = BASE_DIR / "backend" / "app" / "training" / "data" / "exercises"


def import_file(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    for ex in data:
        obj = Exercise(
            name=ex["name"],
            slug=ex["slug"],
            description=ex.get("description"),
            difficulty=ex["difficulty"],
            location=ex.get("location", "any"),
            movement_pattern=ex["movement_pattern"],
            risk_level=ex["risk_level"],
            muscles_primary=ex["muscles_primary"],
            muscles_secondary=ex["muscles_secondary"],
            equipment=ex["equipment"],
            max_additional_load_kg=ex.get("max_additional_load_kg"),
            muscle_load_profile=ex.get("muscle_load_profile"),
        )
        db.session.add(obj)

    db.session.commit()


def run():
    app = create_backend_app()

    with app.app_context():
        import_file(EXERCISES_DIR / "upper_body.json")
        import_file(EXERCISES_DIR / "lower_body.json")
        import_file(EXERCISES_DIR / "core.json")
        import_file(EXERCISES_DIR / "mobility.json")
        import_file(EXERCISES_DIR / "full_body.json")


if __name__ == "__main__":
    run()