import os
import json

from web.app import create_app, db
from web.app.models.recovery.habit import RecoveryHabit

BASE_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "data",
        "habits",
    )
)

FILE_PATH = os.path.join(BASE_DIR, "habits.json")


def run():
    app = create_app()
    with app.app_context():
        with open(FILE_PATH, "r", encoding="utf-8") as f:
            habits = json.load(f)

        created = 0
        updated = 0

        for habit_data in habits:
            slug = habit_data.get("slug")
            if not slug:
                continue

            habit = RecoveryHabit.query.filter_by(slug=slug).first()

            if habit is None:
                habit = RecoveryHabit(slug=slug)
                db.session.add(habit)
                created += 1
            else:
                updated += 1

            habit.name = habit_data.get("name", slug)
            habit.description = habit_data.get("description")
            habit.category = habit_data.get("category")
            habit.points = habit_data.get("points", 0)
            habit.icon = habit_data.get("icon")
            habit.daily_log_limit = habit_data.get("daily_log_limit", 1)
            habit.estimated_minutes = habit_data.get("estimated_minutes", 0)
            habit.recommended_when = habit_data.get("recommended_when", [])
            habit.premium_only = habit_data.get("premium_only", False)
            habit.sort_order = habit_data.get("sort_order", 0)
            habit.is_active = True
            habit.is_archived = False

        db.session.commit()
        print(f"Created {created}, updated {updated} recovery habits")


if __name__ == "__main__":
    run()
