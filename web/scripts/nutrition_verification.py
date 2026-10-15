"""Before/after numbers for the nutrition model, on the real catalog.

    python -m web.scripts.nutrition_verification --baseline-ref b8ce104

``--baseline-ref`` is the git revision holding the *old* implementation
(quality scoring by name, water by label, targets without a protein ceiling).
It is read with ``git show``; nothing is checked out. No database is needed.

What it can and cannot say: the catalog has no ground-truth labels for
"whole" or "processed". The reference set below is a small list labelled by
hand - representative examples, not a measured accuracy. Agreement with it is
reported as such.
"""
from __future__ import annotations

import argparse
import collections
import json
import subprocess
import sys
import types
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

CATALOG = ROOT / "web" / "scripts" / "nutrition_catalog" / "products.json"

# English catalog name -> the class a careful human would give it.
REFERENCE = {
    "whole": [
        "Banana", "Apple", "Broccoli", "Carrot", "Tomato", "Strawberries", "Blueberries",
        "Chicken breast, skinless", "Salmon, wild", "Cod", "Rolled oats", "Buckwheat groats, dry",
        "Lentils, cooked", "Chickpeas, cooked", "Almonds", "Walnuts", "Milk 3.6% (whole)", "Kefir 3.2%",
        "Beef tenderloin", "Pork tenderloin", "Turkey breast", "Shrimp", "Tofu", "Spinach", "Cucumber",
        "Potato", "Wholemeal bread", "Wholemeal pasta, dry", "Scrambled eggs",
    ],
    "processed": [
        "Frankfurters", "Mortadella", "Cooked ham", "Bacon, smoked", "Fruit yogurt", "Milk chocolate",
        "Chocolate chip cookies", "Hamburger", "French fries", "Ice cream", "Ketchup", "Green olives",
        "Frosted corn flakes", "Pizza Margherita", "Strawberry jam",
    ],
    "neutral": [
        "Cheddar", "Mozzarella", "Olive oil, extra virgin", "Butter 82%", "White rice, cooked",
        "Pasta, cooked", "Wheat bread", "Ukrainian borscht with beef", "Hummus", "Orange juice",
    ],
}


def git_show(ref, path):
    return subprocess.run(
        ["git", "show", f"{ref}:{path}"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout


def load_old(ref, path, name):
    """The old module, executed with the database layer stubbed out."""
    stubs = {
        "backend.app.extensions": SimpleNamespace(db=SimpleNamespace(session=None, Model=object)),
        "backend.app.models.nutrition.user_goals": SimpleNamespace(UserGoals=object),
        "backend.app.models.nutrition.user_water": SimpleNamespace(UserWater=object),
        "backend.app.models": SimpleNamespace(Meal=object, MealItem=object, User=object),
        "sqlalchemy": SimpleNamespace(func=None),
    }
    saved = {key: sys.modules.get(key) for key in stubs}
    try:
        for key, value in stubs.items():
            module = types.ModuleType(key)
            module.__dict__.update(vars(value))
            sys.modules[key] = module
        module = types.ModuleType(name)
        exec(compile(git_show(ref, path), path, "exec"), module.__dict__)
        return module
    finally:
        for key, value in saved.items():
            if value is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value


def products():
    return json.loads(CATALOG.read_text(encoding="utf-8"))["products"]


def pct(part, whole):
    return f"{part / whole * 100:5.1f}%" if whole else "   n/a"


def classification(old_quality, new_quality):
    catalog = products()
    total = len(catalog)
    print(f"\n== 1. Classification of the catalog ({total} products) ==\n")

    def old_label(product):
        row = old_quality.calculate_quality(
            [{"name": product["names"]["uk"], "calories": 100, "fiber": 0}]
        )
        whole, processed = row["whole_foods_percent"] == 100, row["processed_foods_percent"] == 100
        return "both" if whole and processed else "whole" if whole else "processed" if processed else "none"

    def new_label(product):
        n = product["per_100g"]
        return new_quality.classify_food(
            product["category"], kcal=n["kcal"], fiber=n.get("fiber"), sugar=n.get("sugar"), salt=n.get("salt"),
            fat=n.get("fat")
        )

    before = collections.Counter(old_label(p) for p in catalog)
    after = collections.Counter(new_label(p) for p in catalog)
    print("before (name substrings, Ukrainian names):", dict(before))
    print("after  (category + nutrients):            ", dict(after))
    print(f"  conflicts (whole AND processed): before {before['both']}, after 0 by construction "
          f"(one class per food; checked in tests)")

    print("\nper category: whole/processed/neutral/unknown after   |   whole/processed/both before")
    by_category = collections.defaultdict(list)
    for product in catalog:
        by_category[product["category"]].append(product)
    for category, items in sorted(by_category.items(), key=lambda kv: -len(kv[1])):
        a = collections.Counter(new_label(p) for p in items)
        b = collections.Counter(old_label(p) for p in items)
        print(f"  {category:<11} n={len(items):>3}   after {a['whole']:>3}/{a['processed']:>3}/{a['neutral']:>3}/"
              f"{a['unknown']:>3}   before {b['whole']:>3}/{b['processed']:>3}/{b['both']:>3}")

    unknown = [p for p in catalog if new_label(p) == "unknown"]
    print(f"\nunknown after: {len(unknown)} products "
          f"({collections.Counter(p['category'] for p in unknown).most_common()})")
    print("  e.g.", [p["names"]["en"] for p in unknown[:6]])
    gaps = collections.Counter()
    for product in catalog:
        for field in ("fiber", "sugar", "saturated_fat", "salt"):
            if product["per_100g"].get(field) is None:
                gaps[field] += 1
    print("catalog values missing (unknown, not zero):", dict(gaps))

    print("\nlocalized names: the old score read the name of the entry, so the interface language decided it.")
    for locale in ("uk", "ru", "en", "pl"):
        hits = sum(
            old_quality.calculate_quality([{"name": p["names"][locale], "calories": 100}])["whole_foods_percent"] == 100
            for p in catalog if locale in p["names"]
        )
        print(f"  old, whole foods found by {locale} names: {hits}")
    print("  new: independent of the name (same result in every language).")


def reference(old_quality, new_quality):
    catalog = {p["names"]["en"]: p for p in products()}
    print("\n== 2. Agreement with a hand-labelled reference set (NOT a measured accuracy) ==\n")
    rows = []
    for expected, names in REFERENCE.items():
        for name in names:
            product = catalog.get(name)
            if product is None:
                print(f"  (not in the catalog: {name})")
                continue
            n = product["per_100g"]
            got = new_quality.classify_food(
                product["category"], kcal=n["kcal"], fiber=n.get("fiber"), sugar=n.get("sugar"), salt=n.get("salt"),
            fat=n.get("fat")
            )
            row = old_quality.calculate_quality([{"name": product["names"]["uk"], "calories": 100, "fiber": 0}])
            whole, processed = row["whole_foods_percent"] == 100, row["processed_foods_percent"] == 100
            old = "both" if whole and processed else "whole" if whole else "processed" if processed else "neutral"
            rows.append((name, expected, got, old))
    new_ok = sum(1 for _, e, g, _ in rows if e == g)
    old_ok = sum(1 for _, e, _, o in rows if e == o)
    print(f"reference foods: {len(rows)}; agree after: {new_ok} ({pct(new_ok, len(rows)).strip()}); "
          f"agree before: {old_ok} ({pct(old_ok, len(rows)).strip()})")
    print("disagreements after (the limits of the rules, listed for review):")
    for name, expected, got, old in rows:
        if expected != got:
            print(f"  - {name}: reference {expected}, now {got}")
    print("limitation: the reference set was written by the author of the rules; it shows representative "
          "behaviour, it is not an independent ground truth.")


def serving_sizes(old_quality, new_quality):
    print("\n== 3. Quality across serving sizes ==\n")
    def day(multiplier):
        return [
            {"name": "Вівсянка", "category": "grains", "calories": 370 * multiplier, "grams": 100 * multiplier,
             "fiber": 10.0 * multiplier, "sugar": 1.0 * multiplier, "saturated_fat": 1.2 * multiplier,
             "salt": 0.02 * multiplier},
            {"name": "Банан", "category": "fruits", "calories": 89 * multiplier, "grams": 100 * multiplier,
             "fiber": 2.6 * multiplier, "sugar": 12.2 * multiplier, "saturated_fat": 0.1 * multiplier,
             "salt": 0.0},
        ]

    print(f"{'kcal':>6} | old score | new score (target 1500 kcal)")
    for multiplier in (0.2, 0.5, 1, 2, 3, 6, 10):
        items = day(multiplier)
        kcal = sum(i["calories"] for i in items)
        old = old_quality.calculate_quality(
            [{"name": i["name"], "calories": i["calories"], "fiber": i["fiber"]} for i in items]
        )["score"]
        new = new_quality.calculate_quality(items, {"calories": 1500})
        print(f"{kcal:>6.0f} | {old:>9} | {new['score']} {('(' + new['reason'] + ')') if new['reason'] else ''}")


def water(old_water, new_water):
    print("\n== 4. Water goals by profile activity level (80 kg man, 30 y, goal: maintenance) ==\n")
    print(f"{'activity':<12} | old L | new L")
    for activity in ("sedentary", "light", "moderate", "active"):
        old = old_water.calculate_water(80, 180, 30, "male", activity, "maintenance")
        new = new_water.calculate_water(80, 30, "male", activity)
        print(f"{activity:<12} | {old:>5} | {new:>5}")
    print("old: only 'moderate' changed the result; new: each level has its own factor.")
    print(f"missing weight: old {old_water.calculate_water(None, 180, 30, 'male', 'light', 'maintenance')!r}"
          f"  new {new_water.calculate_water(None, 30, 'male', 'light')!r}")


def macros(old_cal, new_cal):
    print("\n== 5. Macro energy against the calorie target ==\n")

    def grid():
        for gender in ("male", "female", None):
            for age in (15, 25, 40, 60, 100):
                for weight, height in ((30, 120), (50, 160), (70, 175), (90, 185), (130, 195), (200, 215), (300, 230)):
                    for activity in ("sedentary", "light", "moderate", "active"):
                        for goal in ("fat_loss", "maintenance", "muscle_gain", "strength", "recomp"):
                            yield SimpleNamespace(profile=SimpleNamespace(
                                weight=weight, height=height, age=age, gender=gender,
                                activity=activity, goal=goal))

    for label, module in (("before", old_cal), ("after ", new_cal)):
        count = worst = over_protein = bad_carbs = 0
        for person in grid():
            goals = module.calculate_nutrition_goals(person)
            if goals is None:
                continue
            count += 1
            energy = goals["protein"] * 4 + goals["fat"] * 9 + goals["carbs"] * 4
            worst = max(worst, abs(energy - goals["calories"]))
            over_protein += goals["protein"] * 4 > 0.35 * goals["calories"] + 1
            bad_carbs += goals["carbs"] * 4 < 0.45 * goals["calories"] - 1
        print(f"{label}: profiles {count}, max |macro kcal - target| = {worst:.2f} kcal, "
              f"protein above 35% of energy: {over_protein}, carbohydrate under 45%: {bad_carbs}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--baseline-ref", required=True, help="git revision with the old implementation")
    args = parser.parse_args()

    base = "backend/app/services/nutrition/"
    old_quality = load_old(args.baseline_ref, base + "quality_service.py", "old_quality")
    old_water = load_old(args.baseline_ref, base + "water_service.py", "old_water")
    old_cal = load_old(args.baseline_ref, base + "calories_service.py", "old_cal")

    from backend.app.services.nutrition import calories_service as new_cal
    from backend.app.services.nutrition import quality_service as new_quality
    from backend.app.services.nutrition import water_service as new_water

    classification(old_quality, new_quality)
    reference(old_quality, new_quality)
    serving_sizes(old_quality, new_quality)
    water(old_water, new_water)
    macros(old_cal, new_cal)


if __name__ == "__main__":
    main()
