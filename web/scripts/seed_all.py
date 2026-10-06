"""Fill reference data in a fresh database: exercises, muscles, equipment,
the nutrition product catalog and recovery habits.

Safe to run again: every seed updates existing rows instead of duplicating.

    python -m web.scripts.seed_all
"""

from backend.app.recovery.seed_habits import run as seed_habits
from web.scripts.seed_exercises import run_seed as seed_exercises
from web.scripts.seed_nutrition_products import seed_products


def main() -> None:
    print("== Exercises, muscles, equipment")
    seed_exercises()
    print("== Nutrition products")
    seed_products()
    print("== Recovery habits")
    seed_habits()
    print("Done.")


if __name__ == "__main__":
    main()
