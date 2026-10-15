"""Diet quality: classification, scoring and the data it is fed with.

Expected values are written out by hand (arithmetic in the test), not taken
from the production helpers they check.
"""
import datetime as dt
import json
from pathlib import Path

import pytest

from backend.app.extensions import db
from backend.app.models import Meal, MealItem, Product, ProductName
from backend.app.services.dashboard import aggregator
from backend.app.services.nutrition import quality_service as q
from backend.app.services.nutrition.day_service import get_daily_nutrition_data
from backend.app.services.nutrition.item_service import add_item_service
from backend.app.services.nutrition.recommendation_service import (
    get_nutrition_recommendations,
)
from backend.app.services.nutrition.stats_service import get_day_details

CATALOG = Path(__file__).resolve().parents[2] / "scripts" / "nutrition_catalog" / "products.json"


def food(category, kcal, fiber=None, sugar=None, salt=None):
    """Classification of a food from its values per 100 g."""
    return q.classify_food(category, kcal=kcal, fiber=fiber, sugar=sugar, salt=salt)


# --- classification -------------------------------------------------------

# Typical values per 100 g (kcal, fibre, sugars, salt); the test is about the
# rules, so the numbers only need to be realistic.
NAMED_FOODS = [
    ("banana", "fruits", dict(kcal=89, fiber=2.6, sugar=12.2, salt=0.0), q.WHOLE),
    ("apple", "fruits", dict(kcal=52, fiber=2.4, sugar=10.4, salt=0.0), q.WHOLE),
    ("broccoli", "vegetables", dict(kcal=34, fiber=2.6, sugar=1.7, salt=0.07), q.WHOLE),
    ("chicken breast", "poultry", dict(kcal=110, fiber=0.0, sugar=0.0, salt=0.11), q.WHOLE),
    ("salmon", "fish", dict(kcal=200, fiber=0.0, sugar=0.0, salt=0.1), q.WHOLE),
    ("rolled oats", "grains", dict(kcal=370, fiber=10.0, sugar=1.0, salt=0.02), q.WHOLE),
    ("white rice, cooked", "grains", dict(kcal=130, fiber=0.4, sugar=0.1, salt=0.0), q.NEUTRAL),
    ("cheddar", "cheese", dict(kcal=400, fiber=0.0, sugar=0.1, salt=1.8), q.NEUTRAL),
    ("pork sausage", "meat", dict(kcal=300, fiber=0.0, sugar=1.0, salt=2.2), q.PROCESSED),
    ("fresh pork loin", "meat", dict(kcal=140, fiber=0.0, sugar=0.0, salt=0.1), q.WHOLE),
    ("candy", "sweets", dict(kcal=390, fiber=0.0, sugar=70.0, salt=0.05), q.PROCESSED),
    ("sweetened fruit yogurt", "dairy", dict(kcal=96, fiber=0.2, sugar=13.6, salt=0.12), q.PROCESSED),
    ("plain yogurt", "dairy", dict(kcal=61, fiber=0.0, sugar=4.7, salt=0.11), q.WHOLE),
    ("mixed dish (borscht-like soup)", "prepared", dict(kcal=45, fiber=1.0, sugar=2.0, salt=0.9), q.NEUTRAL),
    ("cola", "beverages", dict(kcal=42, fiber=0.0, sugar=10.6, salt=0.0), q.NEUTRAL),
    ("olive oil", "oils", dict(kcal=884, fiber=0.0, sugar=0.0, salt=0.0), q.NEUTRAL),
    ("potato chips", "snacks", dict(kcal=540, fiber=4.0, sugar=0.5, salt=1.4), q.PROCESSED),
    ("smoked salmon", "fish", dict(kcal=170, fiber=0.0, sugar=0.0, salt=3.5), q.PROCESSED),
    ("butter", "dairy", dict(kcal=717, fiber=0.0, sugar=0.6, salt=0.02, fat=81.0), q.NEUTRAL),
    ("cream 30%", "dairy", dict(kcal=297, fiber=0.0, sugar=2.0, salt=0.07, fat=30.0), q.WHOLE),
    ("canned pickles", "vegetables", dict(kcal=12, fiber=1.0, sugar=1.0, salt=2.0), q.PROCESSED),
    ("unsalted almonds", "nuts", dict(kcal=600, fiber=12.0, sugar=4.0, salt=0.01), q.WHOLE),
    ("ketchup", "sauces", dict(kcal=100, fiber=0.5, sugar=22.8, salt=1.8), q.PROCESSED),
    ("lentils, cooked", "legumes", dict(kcal=116, fiber=7.9, sugar=1.8, salt=0.0), q.WHOLE),
    ("eggs", "eggs", dict(kcal=143, fiber=0.0, sugar=0.4, salt=0.36), q.WHOLE),
    ("chocolate cereal", "grains", dict(kcal=390, fiber=3.0, sugar=31.0, salt=0.4), q.PROCESSED),
]


@pytest.mark.parametrize("name, category, nutrients, expected", NAMED_FOODS, ids=[f[0] for f in NAMED_FOODS])
def test_named_foods_are_classified_by_category_and_nutrients(name, category, nutrients, expected):
    assert q.classify_food(category, **nutrients) == expected


@pytest.mark.parametrize(
    "category, nutrients, expected",
    [
        # Guard boundaries: the value itself is still inside the band.
        ("dairy", dict(kcal=700, sugar=0.5, salt=0.0, fat=79.9), q.WHOLE),
        ("dairy", dict(kcal=700, sugar=0.5, salt=0.0, fat=80.0), q.NEUTRAL),
        ("meat", dict(kcal=150, salt=1.5), q.WHOLE),
        ("meat", dict(kcal=150, salt=1.51), q.PROCESSED),
        ("dairy", dict(kcal=60, sugar=5.0, salt=0.1), q.WHOLE),
        ("dairy", dict(kcal=60, sugar=5.01, salt=0.1), q.PROCESSED),
        ("grains", dict(kcal=100, fiber=1.5, sugar=1, salt=0.0), q.WHOLE),
        ("grains", dict(kcal=100, fiber=1.49, sugar=1, salt=0.0), q.NEUTRAL),
        ("grains", dict(kcal=100, fiber=3, sugar=22.5, salt=0.0), q.WHOLE),
        ("grains", dict(kcal=100, fiber=3, sugar=22.6, salt=0.0), q.PROCESSED),
        # Fruit sugars are intrinsic: dried fruit stays whole.
        ("fruits", dict(kcal=300, fiber=7, sugar=60, salt=0.0), q.WHOLE),
    ],
)
def test_guard_boundaries(category, nutrients, expected):
    assert q.classify_food(category, **nutrients) == expected


@pytest.mark.parametrize("category", [None, "", "other", "not-a-category", "FRUITS-ish"])
def test_unknown_categories_are_unknown_not_guessed(category):
    assert q.classify_food(category, kcal=100, fiber=1, sugar=1, salt=0.1) == q.UNKNOWN


def test_missing_nutrients_make_a_guarded_food_unknown_never_a_zero():
    # Salt decides whether meat is cured; unknown is not "no salt".
    assert q.classify_food("meat", kcal=250, salt=None) == q.UNKNOWN
    assert q.classify_food("meat", kcal=250, salt=0.0) == q.WHOLE
    # Sugar decides whether dairy is sweetened.
    assert q.classify_food("dairy", kcal=60, sugar=None, salt=0.1) == q.UNKNOWN
    assert q.classify_food("dairy", kcal=60, sugar=0.0, salt=0.1) == q.WHOLE
    # Fibre decides whether a cereal food is whole grain.
    assert q.classify_food("grains", kcal=300, fiber=None) == q.UNKNOWN
    assert q.classify_food("grains", kcal=300, fiber=0.0) == q.NEUTRAL
    # Fruit does not depend on the guard nutrients at all.
    assert q.classify_food("fruits", kcal=50) == q.WHOLE
    # Always-processed and always-neutral categories need no nutrient.
    assert q.classify_food("sweets") == q.PROCESSED
    assert q.classify_food("prepared") == q.NEUTRAL


@pytest.mark.parametrize("junk", [float("nan"), float("inf"), "abc", True])
def test_garbage_values_count_as_unknown(junk):
    assert q.classify_food("meat", kcal=100, salt=junk) == q.UNKNOWN


def test_classification_ignores_the_name_and_therefore_the_language():
    base = dict(category="fruits", grams=100, calories=89, fiber=2.6, sugar=12.2, salt=0.0)
    names = ["Банан", "Banana", "Banan", "Банан спелый", "chicken sausage"]  # even a misleading one
    assert {q.classify_item({**base, "name": n}) for n in names} == {q.WHOLE}


def test_classify_item_scales_to_100_g_from_the_entry_amounts():
    # 50 g of sausage: the salt of the entry (1.1 g) is 2.2 g per 100 g.
    entry = dict(category="meat", grams=50, calories=150, fiber=0, sugar=0.5, salt=1.1)
    assert q.classify_item(entry) == q.PROCESSED
    # The same food in 500 g is still the same food.
    big = dict(category="meat", grams=500, calories=1500, fiber=0, sugar=5, salt=11.0)
    assert q.classify_item(big) == q.PROCESSED
    # Without an amount only the category speaks: a guarded one cannot be judged.
    assert q.classify_item(dict(category="meat", grams=None, calories=150, salt=1.1)) == q.UNKNOWN
    assert q.classify_item(dict(category="sweets", grams=None, calories=150)) == q.PROCESSED
    assert q.classify_item(dict(category="fruits", grams=None, calories=50)) == q.WHOLE


def test_every_catalog_product_gets_exactly_one_class_and_the_shares_add_up():
    products = json.loads(CATALOG.read_text(encoding="utf-8"))["products"]
    assert len(products) > 1000
    for product in products:
        n = product["per_100g"]
        label = q.classify_food(
            product["category"], kcal=n["kcal"], fiber=n.get("fiber"),
            sugar=n.get("sugar"), salt=n.get("salt"), fat=n.get("fat"),
        )
        assert label in (q.WHOLE, q.PROCESSED, q.NEUTRAL, q.UNKNOWN), product["key"]

        item = dict(category=product["category"], grams=100, calories=n["kcal"],
                    fiber=n.get("fiber"), sugar=n.get("sugar"), salt=n.get("salt"),
                    saturated_fat=n.get("saturated_fat"), name=product["names"]["en"])
        if n["kcal"] <= 0:
            continue
        result = q.calculate_quality([item], {"calories": n["kcal"] * 4})  # lift the energy floor
        shares = (result["whole_foods_percent"], result["processed_foods_percent"],
                  result["neutral_percent"], result["unclassified_percent"])
        assert sorted(shares)[-1] == 100 and sum(shares) == 100, (product["key"], shares)


def test_localized_names_of_the_catalog_never_change_the_class():
    products = json.loads(CATALOG.read_text(encoding="utf-8"))["products"]
    for product in products[:300]:
        n = product["per_100g"]
        labels = {
            q.classify_item(dict(category=product["category"], grams=100, calories=n["kcal"],
                                 fiber=n.get("fiber"), sugar=n.get("sugar"), salt=n.get("salt"),
                                 name=name))
            for name in product["names"].values()
        }
        assert len(labels) == 1, product["key"]


# --- the score ------------------------------------------------------------

def entry(category, kcal, grams=100, **nutrients):
    return dict(category=category, calories=kcal, grams=grams, name="x", **nutrients)


def test_score_matches_a_hand_calculation():
    oats = entry("grains", 370, 100, fiber=10.0, sugar=1.0, saturated_fat=1.2, salt=0.02)
    candy = entry("sweets", 400, 100, fiber=0.0, sugar=60.0, saturated_fat=10.0, salt=0.1)
    result = q.calculate_quality([oats, candy])

    kcal = 770.0
    whole_share = 370 / kcal            # oats are whole grain: 2.7 g fibre per 100 kcal
    processed_share = 400 / kcal
    fibre_density = 10.0 / kcal * 1000  # g per 1000 kcal, against the default 14
    sugar_energy = (1.0 + 60.0) * 4 / kcal
    saturated_energy = (1.2 + 10.0) * 9 / kcal
    salt_density = (0.02 + 0.1) / kcal * 1000

    parts = {
        "whole_foods": (30, 100 * min(whole_share / 0.5, 1)),
        "processed_foods": (15, 100 * max(0, min(1, 1 - processed_share / 0.5))),
        "fiber": (20, 100 * min(fibre_density / 14, 1)),
        "sugar": (15, 100 * max(0, min(1, 2 - sugar_energy / 0.10))),
        "saturated_fat": (10, 100 * max(0, min(1, 2 - saturated_energy / 0.10))),
        "salt": (10, 100 * max(0, min(1, 2 - salt_density / 2.5))),
    }
    expected = round(sum(w * s for w, s in parts.values()) / sum(w for w, _ in parts.values()))

    assert result["score"] == expected == 64  # 64.29 by hand
    assert result["whole_foods_percent"] == round(whole_share * 100) == 48
    assert result["processed_foods_percent"] == round(processed_share * 100) == 52
    assert result["neutral_percent"] == 0 and result["unclassified_percent"] == 0
    assert set(result["components"]) == set(parts)


def test_quality_is_about_composition_not_amount():
    def day(multiplier):
        return [
            entry("grains", 370 * multiplier, 100 * multiplier, fiber=10.0 * multiplier, sugar=1.0 * multiplier,
                  saturated_fat=1.2 * multiplier, salt=0.02 * multiplier),
            entry("fruits", 89 * multiplier, 100 * multiplier, fiber=2.6 * multiplier, sugar=12.2 * multiplier,
                  saturated_fat=0.1 * multiplier, salt=0.0),
        ]

    # 459 kcal x 3 and x 6 are both above the floor of a 1500 kcal target.
    goals = {"calories": 1500}
    assert q.calculate_quality(day(3), goals)["score"] == q.calculate_quality(day(6), goals)["score"]
    assert q.calculate_quality(day(3), goals)["score"] is not None


def test_a_tiny_serving_does_not_score_the_day():
    apple = [entry("fruits", 30, 60, fiber=1.4, sugar=6.0, saturated_fat=0.0, salt=0.0)]
    result = q.calculate_quality(apple)
    assert result["score"] is None and result["reason"] == "low_energy"
    # Its shares are still reported.
    assert result["whole_foods_percent"] == 100
    # The same apple scores once it is a real part of the day (target 100 kcal).
    assert q.calculate_quality(apple, {"calories": 100})["score"] is not None


def test_energy_floor_follows_the_calorie_target():
    assert q.energy_floor_kcal(None) == 500            # 25% of the 2000 kcal reference
    assert q.energy_floor_kcal({"calories": 0}) == 500  # a zero target is no target
    assert q.energy_floor_kcal({"calories": 3000}) == 750
    assert q.energy_floor_kcal({"calories": 1200}) == 300


def test_unknown_fibre_is_left_out_not_scored_as_zero():
    base = dict(sugar=1.0, saturated_fat=0.5, salt=0.1)
    unknown = [entry("fruits", 600, 700, fiber=None, **base), entry("poultry", 300, 200, fiber=None, **base)]
    zero = [entry("fruits", 600, 700, fiber=0.0, **base), entry("poultry", 300, 200, fiber=0.0, **base)]

    left_out = q.calculate_quality(unknown)
    scored_zero = q.calculate_quality(zero)

    assert "fiber" not in left_out["components"]
    assert left_out["fiber"] is None and left_out["fiber_complete"] is False
    assert scored_zero["components"]["fiber"]["score"] == 0
    assert scored_zero["fiber"] == 0.0 and scored_zero["fiber_complete"] is True
    assert left_out["score"] > scored_zero["score"]


def test_a_nutrient_known_for_a_minority_of_the_energy_is_not_scored():
    # Fibre is stated for 100 of 1000 kcal only.
    items = [entry("fruits", 100, 200, fiber=5.0, sugar=1, saturated_fat=0, salt=0.0),
             entry("poultry", 900, 400, fiber=None, sugar=0, saturated_fat=2, salt=0.4)]
    result = q.calculate_quality(items)
    assert "fiber" not in result["components"]
    assert result["fiber"] == 5.0 and result["fiber_complete"] is False
    assert "sugar" in result["components"]


def test_user_fibre_target_sets_the_fibre_expectation():
    items = [entry("fruits", 1000, 800, fiber=14.0, sugar=1, saturated_fat=0, salt=0.0)]  # 14 g / 1000 kcal
    default = q.calculate_quality(items)["components"]["fiber"]["score"]
    demanding = q.calculate_quality(items, {"calories": 2000, "fiber": 56})["components"]["fiber"]["score"]
    relaxed = q.calculate_quality(items, {"calories": 2000, "fiber": 14})["components"]["fiber"]["score"]
    assert default == 100          # 14 g/1000 kcal meets the default
    assert demanding == 50         # 56 g at 2000 kcal = 28 g/1000 kcal: half met
    assert relaxed == 100
    assert q.fiber_target_density({"calories": 2000, "fiber": 30}) == 15
    assert q.fiber_target_density({"calories": 0, "fiber": 30}) == 14      # no calorie target: default
    assert q.fiber_target_density({"calories": 2000, "fiber": None}) == 14


def test_added_sugar_ignores_intrinsic_sugars():
    assert q.added_sugar_grams(entry("fruits", 100, 100, sugar=12)) == 0
    assert q.added_sugar_grams(entry("vegetables", 100, 100, sugar=5)) == 0
    assert q.added_sugar_grams(entry("dairy", 120, 200, sugar=9.4)) == 0                # milk: lactose only
    assert q.added_sugar_grams(entry("dairy", 120, 200, sugar=27.2)) == pytest.approx(17.2)  # sweetened yogurt
    assert q.added_sugar_grams(entry("sweets", 100, 100, sugar=60)) == 60
    assert q.added_sugar_grams(entry("beverages", 100, 250, sugar=26)) == 26          # sugary drink counts in full
    assert q.added_sugar_grams(entry("sweets", 100, 100, sugar=None)) is None         # unknown, not 0


def test_a_missing_or_zero_energy_day_has_no_score_not_a_zero():
    assert q.calculate_quality([])["score"] is None
    assert q.calculate_quality([])["reason"] == "no_data"
    assert q.calculate_quality(None)["reason"] == "no_data"
    water = q.calculate_quality([entry("beverages", 0, 250, fiber=0.0)])
    assert water["score"] is None and water["reason"] == "no_energy"


def test_partially_specified_entries_score_only_what_is_known():
    # No category, no nutrients: nothing to classify or measure.
    bare = [dict(name="homemade thing", category=None, calories=800, grams=300)]
    result = q.calculate_quality(bare)
    assert result["score"] is None and result["reason"] == "insufficient_data"
    assert result["unclassified_percent"] == 100 and result["whole_foods_percent"] == 0
    # With only the fibre known, the score rests on fibre alone.
    fibre_only = [dict(name="homemade thing", category=None, calories=800, grams=300, fiber=11.2)]
    only = q.calculate_quality(fibre_only)
    assert list(only["components"]) == ["fiber"]
    assert only["score"] == 100  # 11.2 g / 800 kcal = 14 g per 1000 kcal


def test_most_energy_unclassified_leaves_the_shares_out():
    items = [entry("fruits", 100, 200, fiber=2, sugar=1, saturated_fat=0, salt=0.0),
             entry("other", 900, 300, fiber=2, sugar=1, saturated_fat=1, salt=0.1)]
    result = q.calculate_quality(items)
    assert "whole_foods" not in result["components"] and "processed_foods" not in result["components"]
    assert result["unclassified_percent"] == 90


def test_every_class_is_exclusive_in_a_day_of_mixed_food():
    items = [entry("fruits", 100, 200, fiber=2, sugar=10, saturated_fat=0, salt=0.0),
             entry("sweets", 200, 50, fiber=0, sugar=30, saturated_fat=5, salt=0.1),
             entry("cheese", 300, 80, fiber=0, sugar=0, saturated_fat=15, salt=1.5),
             entry("other", 400, 120)]
    r = q.calculate_quality(items)
    assert (r["whole_foods_percent"], r["processed_foods_percent"], r["neutral_percent"],
            r["unclassified_percent"]) == (10, 20, 30, 40)


def test_limit_based_components_are_full_at_the_limit_and_zero_at_twice_the_limit():
    assert q._limit_score(5.0, 5.0) == 100
    assert q._limit_score(7.5, 5.0) == pytest.approx(50)
    assert q._limit_score(10.0, 5.0) == 0
    assert q._limit_score(40.0, 5.0) == 0
    assert q._limit_score(0.0, 5.0) == 100


# --- the data the score is fed with (database) ----------------------------

def make_product(category, names, **nutrients):
    values = dict(kcal_per_100g=100, protein_per_100g=5, fat_per_100g=2, carbs_per_100g=15,
                  fiber_per_100g=2, sugar_per_100g=1, saturated_fat_per_100g=0.5, salt_per_100g=0.05,
                  default_unit="g", grams_per_unit=1, liquid_ml_per_100g=0)
    values.update(nutrients)
    product = Product(source="system", category=category, **values)
    db.session.add(product)
    db.session.flush()
    for locale, name in names.items():
        db.session.add(ProductName(product_id=product.id, locale=locale, name=name))
    db.session.commit()
    return product


def make_meal(user_id, day=None):
    meal = Meal(user_id=user_id, date=day or dt.date.today(), name="Обід", category="Обід")
    db.session.add(meal)
    db.session.commit()
    return meal


def test_a_logged_entry_carries_the_category_of_its_product(app, user):
    banana = make_product("fruits", {"uk": "Банан", "en": "Banana"})
    meal = make_meal(user.id)
    item = add_item_service(user.id, {"meal_id": meal.id, "product_id": banana.id, "amount": 120, "unit": "g"})
    assert item.basis["category"] == "fruits"
    assert q.quality_item_from_entry(item)["category"] == "fruits"


def test_an_old_entry_without_a_category_snapshot_uses_the_product(app, user):
    chicken = make_product("poultry", {"uk": "Куряче філе"}, salt_per_100g=0.1)
    meal = make_meal(user.id)
    old = MealItem(meal_id=meal.id, product_id=chicken.id, name="Куряче філе", amount=200, unit="g",
                   weight=200, calories=220, protein=46, fat=3, carbs=0, fiber=0, sugar=0,
                   saturated_fat=0.9, salt=0.2, basis={"kcal_per_100g": 110})  # before categories were stored
    free = MealItem(meal_id=meal.id, product_id=None, name="Something", amount=1, unit="pcs", weight=100,
                    calories=300, protein=0, fat=0, carbs=0, basis=None)
    db.session.add_all([old, free])
    db.session.commit()

    items = q.quality_items([old, free])
    assert [i["category"] for i in items] == ["poultry", None]
    assert [q.classify_item(i) for i in items] == [q.WHOLE, q.UNKNOWN]


def test_the_same_meal_scores_identically_in_every_interface_language(app, user):
    products = [
        make_product("fruits", {"uk": "Банан", "en": "Banana", "pl": "Banan", "ru": "Банан"}, kcal_per_100g=89, fiber_per_100g=2.6),
        make_product("grains", {"uk": "Вівсянка", "en": "Oats", "pl": "Płatki owsiane", "ru": "Овсянка"},
                     kcal_per_100g=370, fiber_per_100g=10),
        make_product("meat", {"uk": "Ковбаса", "en": "Sausage", "pl": "Kiełbasa", "ru": "Колбаса"},
                     kcal_per_100g=300, salt_per_100g=2.2),
    ]
    results = {}
    for locale in ("uk", "en", "pl", "ru"):
        meal = make_meal(user.id, dt.date(2024, 3, {"uk": 1, "en": 2, "pl": 3, "ru": 4}[locale]))
        for product in products:
            add_item_service(user.id, {"meal_id": meal.id, "product_id": product.id, "amount": 150,
                                       "unit": "g", "locale": locale})
        results[locale] = q.calculate_quality(q.quality_items(Meal.query.get(meal.id).items), {"calories": 1000})
    assert len({json.dumps(r, sort_keys=True) for r in results.values()}) == 1
    names = {i.name for m in Meal.query.all() for i in m.items}
    assert {"Banana", "Банан", "Banan"} <= names           # the entries really carry different names
    assert results["en"]["whole_foods_percent"] > 0 and results["en"]["processed_foods_percent"] > 0


def test_all_screens_agree_on_the_quality_of_the_same_day(app, user):
    from backend.app.models import UserProfile

    db.session.add(UserProfile(user_id=user.id, training_location="home", weight=75, height=180,
                               age=30, gender="male", activity="moderate", goal="maintenance"))
    db.session.commit()
    banana = make_product("fruits", {"uk": "Банан"}, kcal_per_100g=89, fiber_per_100g=2.6, sugar_per_100g=12)
    oats = make_product("grains", {"uk": "Вівсянка"}, kcal_per_100g=370, fiber_per_100g=10)
    candy = make_product("sweets", {"uk": "Цукерки"}, kcal_per_100g=400, fiber_per_100g=0, sugar_per_100g=60)
    meal = make_meal(user.id)
    for product, grams in ((banana, 400), (oats, 250), (candy, 120)):
        add_item_service(user.id, {"meal_id": meal.id, "product_id": product.id, "amount": grams, "unit": "g"})

    today = dt.date.today()
    day = get_daily_nutrition_data(user.id)["quality"]
    details = get_day_details(user.id, today)["quality"]
    dashboard = aggregator.get_today_overview(user.id)["nutrition"]["score"]
    recommended = get_nutrition_recommendations(user.id)["summary"]["quality_score"]

    assert day["score"] is not None
    assert day == details
    assert dashboard == day["score"] == recommended
