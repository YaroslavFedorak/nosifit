import copy
import json
import os

import pytest

from backend.app.training.exercises.catalog import (
    DATA_DIR,
    EQUIPMENT_PATH,
    MUSCLES_PATH,
    ExerciseDataError,
    load_exercise_catalog,
    load_reference_slugs,
    validate_catalog,
    validate_exercise,
)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
TRANSLATIONS_DIR = os.path.join(ROOT, "web", "app", "translations")

# Slugs that existed before the catalog redesign; sessions and plans in the
# database reference them, so they must never disappear.
LEGACY_SLUGS = {
    "plank", "side-plank", "crunches", "bicycle-crunch", "dead-bug", "bird-dog",
    "lying-leg-raise", "superman", "pallof-press", "cable-crunch", "burpee",
    "mountain-climbers", "jumping-jacks", "bear-crawl", "farmer-walk",
    "squat-to-press", "wall-sit", "squat", "box-squat", "lunges", "step-ups",
    "glute-bridge", "rdl-dumbbells", "leg-curl", "leg-extension", "calf-raise",
    "kickback", "neck-tilts", "shoulder-circles", "arm-circles", "cat-cow",
    "thread-the-needle", "thoracic-rotation", "chest-stretch",
    "hip-flexor-stretch", "hamstring-stretch", "quad-stretch", "calf-stretch",
    "worlds-greatest-stretch", "push-ups", "bench-dips", "pull-ups",
    "seated-row", "bench-press", "overhead-press", "bicep-curl",
    "tricep-pushdown", "lateral-raises", "reverse-fly",
}

DURATION_SLUGS = {
    "plank", "side-plank", "rkc-plank", "wall-sit", "dead-hang",
    "hollow-body-hold", "arch-hold", "l-sit-hold", "handstand-hold",
    "wall-handstand-hold", "isometric-squat-hold", "copenhagen-plank",
    "glute-bridge-hold", "farmer-walk", "suitcase-carry", "sprint",
    "sled-push", "jump-rope", "battle-rope-waves",
}

REPS_SLUGS = {
    "push-ups", "squat", "barbell-back-squat", "bench-press", "pull-ups",
    "dumbbell-row", "hip-thrust", "cable-crunch", "bulgarian-split-squat",
}

NO_EXTRA_LOAD_SLUGS = {"plank", "dead-bug", "bird-dog", "hollow-body-hold"}


@pytest.fixture(scope="module")
def catalog():
    return load_exercise_catalog()


@pytest.fixture(scope="module")
def by_slug(catalog):
    return {item["slug"]: item for item in catalog}


@pytest.fixture
def muscles():
    return load_reference_slugs(MUSCLES_PATH)


@pytest.fixture
def equipment():
    return load_reference_slugs(EQUIPMENT_PATH)


def test_catalog_loads_without_errors(catalog):
    assert 200 <= len(catalog) <= 220


def test_catalog_keeps_legacy_slugs(by_slug):
    assert LEGACY_SLUGS <= set(by_slug)


def test_static_exercises_are_duration_based(by_slug):
    for slug in DURATION_SLUGS:
        item = by_slug[slug]
        assert item["measurement_type"] == "duration", slug
        assert "seconds_min" in item["prescription"], slug
        assert "reps_min" not in item["prescription"], slug


def test_strength_exercises_are_rep_based(by_slug):
    for slug in REPS_SLUGS:
        item = by_slug[slug]
        assert item["measurement_type"] == "reps", slug
        assert "reps_min" in item["prescription"], slug
        assert "seconds_min" not in item["prescription"], slug


def test_core_holds_carry_no_additional_load(by_slug):
    for slug in NO_EXTRA_LOAD_SLUGS:
        assert by_slug[slug]["max_additional_load_kg"] is None, slug


def test_loaded_exercises_declare_load_limits(by_slug):
    assert by_slug["bench-press"]["load_type"] == "external"
    assert by_slug["bench-press"]["max_additional_load_kg"] > 0
    assert by_slug["pull-ups"]["load_type"] == "bodyweight"
    assert by_slug["pull-ups"]["max_additional_load_kg"] > 0
    assert by_slug["cable-crunch"]["load_type"] == "cable"
    assert by_slug["leg-press"]["load_type"] == "machine"


def test_coverage_is_balanced(catalog):
    primary = {}
    for item in catalog:
        for muscle in item["muscles_primary"]:
            primary[muscle] = primary.get(muscle, 0) + 1

    for muscle in (
        "quads", "hamstrings", "glutes", "calves", "chest", "lats",
        "upper-back", "traps", "shoulders", "biceps", "triceps", "forearms",
        "abs", "obliques", "core", "lower-back", "adductors",
    ):
        assert primary.get(muscle, 0) >= 4, muscle


def test_every_exercise_is_translated(catalog):
    slugs = {item["slug"] for item in catalog}

    for lang in ("en", "uk", "ru", "pl"):
        path = os.path.join(TRANSLATIONS_DIR, lang, "exercises.json")
        with open(path, encoding="utf-8") as file:
            translations = json.load(file)

        assert slugs <= set(translations), lang
        names = [value["name"].strip().lower() for value in translations.values()]
        assert len(names) == len(set(names)), f"duplicate names in {lang}"


def test_split_templates_reference_catalog_slugs(by_slug):
    splits = os.path.join(DATA_DIR, "templates", "splits")

    for filename in os.listdir(splits):
        with open(os.path.join(splits, filename), encoding="utf-8") as file:
            template = json.load(file)

        for day in template["days"].values():
            for exercise in day["exercises"]:
                assert exercise["id"] in by_slug, (filename, exercise["id"])


# ------------------------------------------------------------- validation


def _valid_reps():
    return {
        "slug": "test-push",
        "name": "Test Push",
        "movement_pattern": "push",
        "difficulty": 2,
        "risk_level": 1,
        "equipment": ["dumbbells"],
        "load_type": "external",
        "max_additional_load_kg": 50,
        "measurement_type": "reps",
        "prescription": {"sets": 3, "reps_min": 8, "reps_max": 12},
        "muscles_primary": ["chest"],
        "muscles_secondary": ["triceps"],
        "muscle_load_profile": {"chest": 0.7, "triceps": 0.3},
    }


def _valid_duration():
    return {
        "slug": "test-hold",
        "name": "Test Hold",
        "movement_pattern": "anti-extension",
        "difficulty": 1,
        "risk_level": 1,
        "equipment": ["bodyweight"],
        "load_type": "bodyweight",
        "bodyweight_ratio": 0.4,
        "max_additional_load_kg": None,
        "measurement_type": "duration",
        "prescription": {"sets": 3, "seconds_min": 20, "seconds_max": 60},
        "muscles_primary": ["core"],
        "muscles_secondary": [],
        "muscle_load_profile": {"core": 1.0},
    }


def _errors(item, muscles, equipment):
    return validate_exercise(item, muscles, equipment)


def test_valid_definitions_pass(muscles, equipment):
    assert _errors(_valid_reps(), muscles, equipment) == []
    assert _errors(_valid_duration(), muscles, equipment) == []


def _mutate(base, **changes):
    item = copy.deepcopy(base)
    for key, value in changes.items():
        if value is _DELETE:
            item.pop(key, None)
        else:
            item[key] = value
    return item


_DELETE = object()


@pytest.mark.parametrize(
    "base, changes, fragment",
    [
        (_valid_reps, {"name": _DELETE}, "missing required fields"),
        (_valid_reps, {"measurement_type": "distance"}, "measurement_type"),
        (_valid_reps, {"difficulty": 0}, "difficulty"),
        (_valid_reps, {"difficulty": 2.5}, "difficulty"),
        (_valid_reps, {"risk_level": 9}, "risk_level"),
        (_valid_reps, {"movement_pattern": "pushing"}, "movement_pattern"),
        (_valid_reps, {"equipment": []}, "equipment"),
        (_valid_reps, {"equipment": "dumbbells"}, "equipment"),
        (_valid_reps, {"equipment": ["hoverboard"]}, "unknown equipment"),
        (_valid_reps, {"slug": "Test Push"}, "kebab-case"),
        (_valid_reps, {"name": "Віджимання"}, "canonical English"),
        (_valid_reps, {"muscles_primary": []}, "must not be empty"),
        (_valid_reps, {"muscles_primary": ["pecs"]}, "unknown muscles"),
        (
            _valid_reps,
            {"muscle_load_profile": {"chest": 1.4, "triceps": 0.3}},
            "must be in (0, 1]",
        ),
        (
            _valid_reps,
            {"muscle_load_profile": {"chest": 0.5, "triceps": 0.2}},
            "sums to",
        ),
        (
            _valid_reps,
            {"muscle_load_profile": {"chest": 1.0}},
            "cover exactly",
        ),
        (
            _valid_reps,
            {"muscle_load_profile": {"chest": 0.3, "triceps": 0.7}},
            "secondary muscle carries more load",
        ),
        (
            _valid_reps,
            {"muscles_secondary": ["chest"]},
            "both primary and secondary",
        ),
        (_valid_reps, {"max_additional_load_kg": -5}, "max_additional_load_kg"),
        (_valid_reps, {"max_additional_load_kg": None}, "requires max_additional"),
        (_valid_reps, {"bodyweight_ratio": 0.5}, "only valid for load_type"),
        (_valid_reps, {"load_type": "magic"}, "load_type must be one of"),
        (_valid_reps, {"load_type": "cable"}, "requires one of"),
        (
            _valid_reps,
            {"prescription": {"sets": 3, "reps_min": 12, "reps_max": 8}},
            "exceeds",
        ),
        (
            _valid_reps,
            {"prescription": {"sets": 3, "reps_min": 8, "reps_max": 12,
                              "seconds_min": 30}},
            "not valid for measurement_type 'reps'",
        ),
        (
            _valid_duration,
            {"prescription": {"sets": 3, "reps_min": 30, "reps_max": 30}},
            "not valid for measurement_type 'duration'",
        ),
        (
            _valid_duration,
            {"prescription": {"sets": 3, "seconds_min": 1, "seconds_max": 60}},
            "seconds_min",
        ),
        (_valid_duration, {"bodyweight_ratio": None}, "bodyweight_ratio"),
        (_valid_duration, {"bodyweight_ratio": 3}, "bodyweight_ratio"),
        (
            _valid_duration,
            {"equipment": ["bodyweight", "bench"]},
            "cannot be combined",
        ),
        (_valid_duration, {"color": "red"}, "unknown fields"),
    ],
)
def test_validator_rejects_malformed_data(base, changes, fragment, muscles, equipment):
    errors = _errors(_mutate(base(), **changes), muscles, equipment)

    assert any(fragment in error for error in errors), errors


def test_catalog_rejects_duplicates(muscles, equipment):
    first = _valid_reps()
    duplicate_slug = _mutate(_valid_reps(), name="Another Name")
    duplicate_name = _mutate(_valid_reps(), slug="test-push-2")

    errors = validate_catalog([first, duplicate_slug, duplicate_name], muscles, equipment)

    assert any("duplicate slug 'test-push'" in error for error in errors)
    assert any("duplicate exercise name 'test push'" in error for error in errors)


def test_loader_fails_fast_on_bad_file(tmp_path):
    bad = _mutate(_valid_duration(), prescription={"sets": 3, "reps_min": 30, "reps_max": 30})
    (tmp_path / "broken.json").write_text(json.dumps([bad]), encoding="utf-8")

    with pytest.raises(ExerciseDataError) as error:
        load_exercise_catalog(str(tmp_path))

    assert "test-hold" in str(error.value)
