"""Static exercise catalog: schema, validation and loading.

The catalog lives in ``backend/app/training/data/exercises/*.json`` and is
copied into ``te_exercises`` by ``web/scripts/seed_exercises.py``. Every record
is validated here before it can reach the database, so malformed data fails
fast instead of silently producing wrong training loads.

Run ``python -m backend.app.training.exercises.catalog`` to validate the data
and print a coverage summary.
"""

import json
import math
import os
import re
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional

DATA_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data")
)
EXERCISES_DIR = os.path.join(DATA_DIR, "exercises")
MUSCLES_PATH = os.path.join(DATA_DIR, "muscles", "muscles.json")
EQUIPMENT_PATH = os.path.join(DATA_DIR, "equipment", "equipment.json")

# How the exercise is prescribed and logged.
MEASUREMENT_REPS = "reps"
MEASUREMENT_DURATION = "duration"
MEASUREMENT_TYPES = (MEASUREMENT_REPS, MEASUREMENT_DURATION)

# Where the resistance comes from. Only bodyweight exercises carry a
# bodyweight_ratio; only external/machine/cable loads are measured in kg.
LOAD_BODYWEIGHT = "bodyweight"
LOAD_EXTERNAL = "external"
LOAD_MACHINE = "machine"
LOAD_CABLE = "cable"
LOAD_BAND = "band"
LOAD_NONE = "none"
LOAD_TYPES = (
    LOAD_BODYWEIGHT,
    LOAD_EXTERNAL,
    LOAD_MACHINE,
    LOAD_CABLE,
    LOAD_BAND,
    LOAD_NONE,
)
LOAD_TYPES_REQUIRING_KG = (LOAD_EXTERNAL, LOAD_MACHINE, LOAD_CABLE)

# Equipment that must be present for a given load type.
LOAD_TYPE_EQUIPMENT = {
    LOAD_EXTERNAL: {
        "barbell",
        "dumbbells",
        "kettlebell",
        "medicine-ball",
        "sled",
        "trap-bar",
    },
    LOAD_MACHINE: {"machine"},
    LOAD_CABLE: {"cable"},
    LOAD_BAND: {"band"},
}

MOVEMENT_PATTERNS = (
    "squat",
    "hinge",
    "lunge",
    "push",
    "pull",
    "carry",
    "rotation",
    "anti-rotation",
    "anti-extension",
    "anti-lateral-flexion",
    "core",
    "isolation",
    "locomotion",
    "jump",
    "full-body",
    "mobility",
)

DIFFICULTY_MIN, DIFFICULTY_MAX = 1, 5
RISK_MIN, RISK_MAX = 1, 5

SETS_RANGE = (1, 10)
REPS_RANGE = (1, 100)
SECONDS_RANGE = (5, 600)
MAX_ADDITIONAL_LOAD_LIMIT_KG = 500

PROFILE_SUM_TOLERANCE = 0.02

PRESCRIPTION_KEYS = {
    MEASUREMENT_REPS: {"sets", "reps_min", "reps_max", "per_side"},
    MEASUREMENT_DURATION: {"sets", "seconds_min", "seconds_max", "per_side"},
}

REQUIRED_FIELDS = (
    "slug",
    "name",
    "difficulty",
    "movement_pattern",
    "risk_level",
    "equipment",
    "load_type",
    "measurement_type",
    "prescription",
    "muscles_primary",
    "muscles_secondary",
    "muscle_load_profile",
)

OPTIONAL_FIELDS = (
    "description",
    "bodyweight_ratio",
    "max_additional_load_kg",
)

SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
CYRILLIC_RE = re.compile(r"[Ѐ-ӿ]")


class ExerciseDataError(ValueError):
    def __init__(self, errors: List[str]):
        self.errors = errors
        preview = "\n".join(f"  - {error}" for error in errors[:50])
        more = f"\n  ... and {len(errors) - 50} more" if len(errors) > 50 else ""
        super().__init__(f"Invalid exercise data:\n{preview}{more}")


def _is_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_int_range(errors, label, value, bounds):
    low, high = bounds
    if not _is_int(value) or not low <= value <= high:
        errors.append(f"{label} must be an integer between {low} and {high}")
        return False
    return True


def _validate_prescription(errors, prefix, measurement, prescription):
    if not isinstance(prescription, dict):
        errors.append(f"{prefix}: prescription must be an object")
        return

    allowed = PRESCRIPTION_KEYS.get(measurement)
    if allowed is None:
        return

    foreign = sorted(set(prescription) - allowed)
    if foreign:
        errors.append(
            f"{prefix}: prescription fields {foreign} are not valid "
            f"for measurement_type '{measurement}'"
        )

    _validate_int_range(
        errors, f"{prefix}: prescription.sets", prescription.get("sets"), SETS_RANGE
    )

    if measurement == MEASUREMENT_REPS:
        low_key, high_key, bounds = "reps_min", "reps_max", REPS_RANGE
    else:
        low_key, high_key, bounds = "seconds_min", "seconds_max", SECONDS_RANGE

    low_ok = _validate_int_range(
        errors, f"{prefix}: prescription.{low_key}", prescription.get(low_key), bounds
    )
    high_ok = _validate_int_range(
        errors,
        f"{prefix}: prescription.{high_key}",
        prescription.get(high_key),
        bounds,
    )
    if low_ok and high_ok and prescription[low_key] > prescription[high_key]:
        errors.append(f"{prefix}: prescription.{low_key} exceeds {high_key}")

    if "per_side" in prescription and not isinstance(prescription["per_side"], bool):
        errors.append(f"{prefix}: prescription.per_side must be a boolean")


def _validate_load(errors, prefix, item, equipment):
    load_type = item.get("load_type")
    if load_type not in LOAD_TYPES:
        errors.append(f"{prefix}: load_type must be one of {list(LOAD_TYPES)}")
        return

    required_equipment = LOAD_TYPE_EQUIPMENT.get(load_type)
    if required_equipment and isinstance(equipment, list):
        if not required_equipment.intersection(equipment):
            errors.append(
                f"{prefix}: load_type '{load_type}' requires one of "
                f"{sorted(required_equipment)} in equipment"
            )

    ratio = item.get("bodyweight_ratio")
    if load_type == LOAD_BODYWEIGHT:
        if not _is_number(ratio) or not 0 < ratio <= 1.5:
            errors.append(
                f"{prefix}: bodyweight exercises need bodyweight_ratio in (0, 1.5]"
            )
    elif ratio is not None:
        errors.append(
            f"{prefix}: bodyweight_ratio is only valid for load_type 'bodyweight'"
        )

    max_load = item.get("max_additional_load_kg")
    if max_load is not None and (
        not _is_number(max_load)
        or max_load <= 0
        or max_load > MAX_ADDITIONAL_LOAD_LIMIT_KG
    ):
        errors.append(
            f"{prefix}: max_additional_load_kg must be null or a number in "
            f"(0, {MAX_ADDITIONAL_LOAD_LIMIT_KG}]"
        )
        return

    if load_type in LOAD_TYPES_REQUIRING_KG and max_load is None:
        errors.append(
            f"{prefix}: load_type '{load_type}' requires max_additional_load_kg"
        )
    if load_type in (LOAD_BAND, LOAD_NONE) and max_load is not None:
        errors.append(
            f"{prefix}: load_type '{load_type}' cannot have max_additional_load_kg"
        )


def _validate_muscles(errors, prefix, item, known_muscles):
    primary = item.get("muscles_primary")
    secondary = item.get("muscles_secondary")
    profile = item.get("muscle_load_profile")

    lists_ok = True
    for label, value, allow_empty in (
        ("muscles_primary", primary, False),
        ("muscles_secondary", secondary, True),
    ):
        if not isinstance(value, list) or not all(isinstance(m, str) for m in value):
            errors.append(f"{prefix}: {label} must be a list of muscle slugs")
            lists_ok = False
            continue
        if not value and not allow_empty:
            errors.append(f"{prefix}: {label} must not be empty")
        if len(set(value)) != len(value):
            errors.append(f"{prefix}: {label} contains duplicates")
        unknown = sorted(set(value) - known_muscles) if known_muscles else []
        if unknown:
            errors.append(f"{prefix}: {label} has unknown muscles {unknown}")

    if lists_ok:
        overlap = sorted(set(primary) & set(secondary))
        if overlap:
            errors.append(f"{prefix}: muscles {overlap} are both primary and secondary")

    if not isinstance(profile, dict) or not profile:
        errors.append(f"{prefix}: muscle_load_profile must be a non-empty object")
        return

    for muscle, value in profile.items():
        if not _is_number(value) or not 0 < value <= 1:
            errors.append(
                f"{prefix}: muscle_load_profile['{muscle}'] must be in (0, 1]"
            )
            return

    total = sum(profile.values())
    if abs(total - 1.0) > PROFILE_SUM_TOLERANCE:
        errors.append(
            f"{prefix}: muscle_load_profile sums to {total:.3f}, expected 1.0"
        )

    if not lists_ok:
        return

    expected = set(primary) | set(secondary)
    if set(profile) != expected:
        missing = sorted(expected - set(profile))
        extra = sorted(set(profile) - expected)
        errors.append(
            f"{prefix}: muscle_load_profile must cover exactly the primary and "
            f"secondary muscles (missing {missing}, unexpected {extra})"
        )
        return

    if secondary and min(profile[m] for m in primary) < max(
        profile[m] for m in secondary
    ):
        errors.append(
            f"{prefix}: a secondary muscle carries more load than a primary one"
        )


def validate_exercise(
    item: Any,
    known_muscles: Optional[Iterable[str]] = None,
    known_equipment: Optional[Iterable[str]] = None,
) -> List[str]:
    """Return a list of problems with one exercise definition."""
    if not isinstance(item, dict):
        return ["exercise definition must be an object"]

    slug = item.get("slug")
    prefix = f"'{slug}'" if isinstance(slug, str) and slug else "<no slug>"
    errors: List[str] = []

    missing = [field for field in REQUIRED_FIELDS if field not in item]
    if missing:
        errors.append(f"{prefix}: missing required fields {missing}")

    unknown_fields = sorted(set(item) - set(REQUIRED_FIELDS) - set(OPTIONAL_FIELDS))
    if unknown_fields:
        errors.append(f"{prefix}: unknown fields {unknown_fields}")

    if not isinstance(slug, str) or not SLUG_RE.match(slug):
        errors.append(f"{prefix}: slug must be lowercase kebab-case")

    name = item.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append(f"{prefix}: name must be a non-empty string")
    elif CYRILLIC_RE.search(name):
        errors.append(
            f"{prefix}: name must be the canonical English name; "
            "localized names belong in web/app/translations/*/exercises.json"
        )

    if "difficulty" in item:
        _validate_int_range(
            errors,
            f"{prefix}: difficulty",
            item["difficulty"],
            (DIFFICULTY_MIN, DIFFICULTY_MAX),
        )
    if "risk_level" in item:
        _validate_int_range(
            errors, f"{prefix}: risk_level", item["risk_level"], (RISK_MIN, RISK_MAX)
        )

    if item.get("movement_pattern") not in MOVEMENT_PATTERNS:
        errors.append(
            f"{prefix}: movement_pattern must be one of {list(MOVEMENT_PATTERNS)}"
        )

    equipment = item.get("equipment")
    known_equipment = set(known_equipment or [])
    if (
        not isinstance(equipment, list)
        or not equipment
        or not all(isinstance(e, str) and e for e in equipment)
    ):
        errors.append(f"{prefix}: equipment must be a non-empty list of slugs")
        equipment = None
    else:
        if len(set(equipment)) != len(equipment):
            errors.append(f"{prefix}: equipment contains duplicates")
        unknown = sorted(set(equipment) - known_equipment) if known_equipment else []
        if unknown:
            errors.append(f"{prefix}: unknown equipment {unknown}")
        if "bodyweight" in equipment and len(equipment) > 1:
            errors.append(
                f"{prefix}: 'bodyweight' means no equipment and cannot be combined"
            )

    measurement = item.get("measurement_type")
    if measurement not in MEASUREMENT_TYPES:
        errors.append(
            f"{prefix}: measurement_type must be one of {list(MEASUREMENT_TYPES)}"
        )
    if "prescription" in item:
        _validate_prescription(errors, prefix, measurement, item["prescription"])

    _validate_load(errors, prefix, item, equipment)
    _validate_muscles(errors, prefix, item, set(known_muscles or []))

    description = item.get("description")
    if description is not None and not isinstance(description, str):
        errors.append(f"{prefix}: description must be a string")

    return errors


def validate_catalog(
    items: List[Any],
    known_muscles: Optional[Iterable[str]] = None,
    known_equipment: Optional[Iterable[str]] = None,
) -> List[str]:
    """Validate every exercise plus catalog-wide uniqueness rules."""
    errors: List[str] = []
    known_muscles = set(known_muscles or [])
    known_equipment = set(known_equipment or [])

    for item in items:
        errors.extend(validate_exercise(item, known_muscles, known_equipment))

    dicts = [item for item in items if isinstance(item, dict)]

    slugs = Counter(item.get("slug") for item in dicts)
    for slug, count in slugs.items():
        if slug and count > 1:
            errors.append(f"duplicate slug '{slug}' ({count} records)")

    names = Counter(
        str(item.get("name", "")).strip().lower() for item in dicts if item.get("name")
    )
    for name, count in names.items():
        if count > 1:
            errors.append(f"duplicate exercise name '{name}' ({count} records)")

    return errors


def _read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def load_reference_slugs(path: str) -> List[str]:
    return [item["slug"] for item in _read_json(path)]


def load_raw_exercises(directory: str = EXERCISES_DIR) -> List[Any]:
    items: List[Any] = []
    for filename in sorted(os.listdir(directory)):
        if not filename.endswith(".json"):
            continue
        data = _read_json(os.path.join(directory, filename))
        if not isinstance(data, list):
            raise ExerciseDataError([f"{filename}: top level must be a list"])
        items.extend(data)
    return items


def load_exercise_catalog(
    directory: str = EXERCISES_DIR,
    muscles_path: str = MUSCLES_PATH,
    equipment_path: str = EQUIPMENT_PATH,
) -> List[Dict[str, Any]]:
    """Load and validate the whole catalog; raise ExerciseDataError on problems."""
    items = load_raw_exercises(directory)
    errors = validate_catalog(
        items,
        known_muscles=load_reference_slugs(muscles_path),
        known_equipment=load_reference_slugs(equipment_path),
    )
    if errors:
        raise ExerciseDataError(errors)
    return items


def _summary(items: List[Dict[str, Any]]) -> str:
    lines = [f"{len(items)} exercises"]
    for label, key in (
        ("measurement_type", "measurement_type"),
        ("load_type", "load_type"),
        ("movement_pattern", "movement_pattern"),
        ("difficulty", "difficulty"),
        ("risk_level", "risk_level"),
    ):
        counts = Counter(item[key] for item in items)
        lines.append(f"{label}: {dict(sorted(counts.items()))}")
    primary = Counter(m for item in items for m in item["muscles_primary"])
    lines.append(f"primary muscle coverage: {dict(sorted(primary.items()))}")
    equipment = Counter(e for item in items for e in item["equipment"])
    lines.append(f"equipment usage: {dict(sorted(equipment.items()))}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(_summary(load_exercise_catalog()))
