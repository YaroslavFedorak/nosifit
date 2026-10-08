"""Fixtures for the pure training-model tests (no database needed).

The catalog comes from the real exercise JSON, so the tests exercise the same
muscle_load_profile data the application uses.
"""

import pytest

from backend.app.services.training.model.records import ExerciseInfo
from backend.app.training.exercises.catalog import load_exercise_catalog
from tm_helpers import NOW


@pytest.fixture(scope="session")
def catalog():
    items = {}
    for raw in load_exercise_catalog():
        data = dict(raw)
        data["id"] = data["slug"]
        info = ExerciseInfo.from_mapping(data)
        items[info.id] = info
    return items


@pytest.fixture
def now():
    return NOW
