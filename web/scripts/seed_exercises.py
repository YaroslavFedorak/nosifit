import json
import os
import sys
from web.app import create_app, db

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "app", "training_engine", "data")
)


def load_json(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def load_all_from_dir(path):
    items = []
    if not os.path.exists(path):
        return items
    for fname in os.listdir(path):
        if fname.endswith(".json"):
            fpath = os.path.join(path, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
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
        from web.app.training_engine.models.muscle import Muscle
        from web.app.training_engine.models.equipment import TEEquipment
        from web.app.training_engine.models.exercise import Exercise

        muscles = load_json(muscles_path)
        equipment = load_json(equipment_path)
        exercises = load_all_from_dir(exercises_dir)

        for m in muscles:
            slug = m.get("slug")
            name = m.get("name")
            desc = m.get("description")
            if not slug or not name:
                continue
            obj = Muscle.query.filter_by(slug=slug).first()
            if not obj:
                obj = Muscle(slug=slug, name=name, description=desc)
                db.session.add(obj)

        for e in equipment:
            slug = e.get("slug")
            name = e.get("name")
            desc = e.get("description")
            tags = e.get("tags", [])
            if not slug or not name:
                continue
            obj = TEEquipment.query.filter_by(slug=slug).first()
            if not obj:
                obj = TEEquipment(slug=slug, name=name, description=desc)
                obj.set_tags(tags)
                db.session.add(obj)

        db.session.flush()

        for it in exercises:
            slug = it.get("slug") or it["name"].lower().replace(" ", "-")
            if not slug:
                continue

            ex = Exercise.query.filter_by(slug=slug).first()
            if ex:
                continue

            ex = Exercise(
                name=it["name"],
                slug=slug,
                description=it.get("description"),
                difficulty=it.get("difficulty", 1),
                location=it.get("location", "any"),
                movement_pattern=it.get("movement_pattern"),
                risk_level=it.get("risk_level", 1),
                muscles_primary=it.get("muscles_primary", []),
                muscles_secondary=it.get("muscles_secondary", []),
                progression=json.dumps(it.get("progression", [])),
                regression=json.dumps(it.get("regression", [])),
            )
            db.session.add(ex)
            db.session.flush()

            for mslug in it.get("muscles_primary", []):
                m = Muscle.query.filter_by(slug=mslug).first()
                if m and m not in ex.muscles:
                    ex.muscles.append(m)

            for mslug in it.get("muscles_secondary", []):
                m = Muscle.query.filter_by(slug=mslug).first()
                if m and m not in ex.muscles:
                    ex.muscles.append(m)

            for ename in it.get("equipment", []):
                eslug = ename.lower().replace(" ", "-")
                eq = TEEquipment.query.filter_by(slug=eslug).first()
                if eq:
                    ex.equipment.append(eq)

        db.session.commit()
        print(
            f"Seed complete: {len(muscles)} muscles, "
            f"{len(equipment)} equipment items, "
            f"{len(exercises)} exercises processed."
        )


if __name__ == "__main__":
    run_seed()
