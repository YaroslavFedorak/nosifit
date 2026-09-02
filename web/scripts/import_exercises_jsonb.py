import json
from web.app import db
from web.app.training_engine.models.exercise import Exercise


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


import_file("web/app/training_engine/data/exercises/upper_body.json")
import_file("web/app/training_engine/data/exercises/lower_body.json")
import_file("web/app/training_engine/data/exercises/core.json")
import_file("web/app/training_engine/data/exercises/mobility.json")
import_file("web/app/training_engine/data/exercises/full_body.json")
