"""muscle_loads holds {muscle_slug: effective_sets}; older rows held exercise ids."""

import datetime as dt
import importlib.util
import os
import sys
from types import SimpleNamespace

import pytest

from backend.app.extensions import db
from backend.app.models.training_session import SessionExercise, TrainingSession
from backend.app.services.recovery import constants as recovery_constants
from backend.app.training.exercises.catalog import (
    MUSCLES_PATH,
    known_muscle_slugs,
    load_exercise_catalog,
    load_reference_slugs,
)
from backend.app.training.models.exercise import Exercise
from backend.app.training.training_analysis.analyzers.muscles import (
    _add_stored_muscle_loads,
    analyse_muscles,
)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
EXERCISE_ID = "0b6d2df5-5a53-4c6a-9d4c-3d1f2f6f9a11"


def _session(muscle_loads, days_ago=1):
    started = dt.datetime.utcnow() - dt.timedelta(days=days_ago)
    return SimpleNamespace(started_at=started, muscle_loads=muscle_loads, exercises=[])


def _load_migration():
    path = os.path.join(ROOT, "migrations", "versions", "f2b8d6a4c0e1_strip_legacy_muscle_load_keys.py")
    spec = importlib.util.spec_from_file_location("strip_legacy_muscle_load_keys", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_known_muscle_slugs_come_from_muscles_json():
    assert known_muscle_slugs() == frozenset(load_reference_slugs(MUSCLES_PATH))
    assert {"chest", "quads", "lats"} <= known_muscle_slugs()


def test_stored_loads_ignore_exercise_id_keys():
    totals = {}
    added = _add_stored_muscle_loads(totals, _session({EXERCISE_ID: 480.0, "Chest": 4.0}))
    assert added is True
    assert totals == {"chest": 4.0}


def test_session_with_only_legacy_keys_is_not_treated_as_stored():
    totals = {}
    assert _add_stored_muscle_loads(totals, _session({EXERCISE_ID: 480.0})) is False
    assert totals == {}


def test_analyse_muscles_never_reports_exercise_ids():
    sessions = [
        _session({EXERCISE_ID: 900.0, "chest": 6.0, "triceps": 3.0}),
        _session({EXERCISE_ID: 100.0, "lats": 5.0}, days_ago=2),
    ]
    result = analyse_muscles(sessions, dt.date.today())
    names = set(result["totals"]) | set(result["weak"]) | set(result["overloaded"]) | set(result["balanced"])
    assert names == {"chest", "triceps", "lats"}
    assert result["totals"]["chest"] == 6.0


def test_unused_muscle_load_thresholds_are_gone():
    assert not hasattr(recovery_constants, "MUSCLE_LOW_LOAD")
    assert not hasattr(recovery_constants, "MUSCLE_HIGH_LOAD")


def test_migration_keeps_only_muscle_slugs():
    clean = _load_migration()._clean
    known = known_muscle_slugs()
    assert clean({EXERCISE_ID: 480.0, "chest": 4.0}, known) == {"chest": 4.0}
    assert clean({EXERCISE_ID: 480.0}, known) == {}
    assert clean(None, known) == {}
    assert clean([1, 2], known) == {}


def test_migration_chains_after_current_head():
    assert _load_migration().down_revision == "a7c3e9d1f4b6"


# --- rebuild script (database) ---------------------------------------------


@pytest.fixture
def catalog(app):
    rows = {}
    for item in load_exercise_catalog():
        exercise = Exercise(**item)
        db.session.add(exercise)
        rows[item["slug"]] = exercise
    db.session.commit()
    return rows


def _finished_session(user, catalog, muscle_loads):
    finished = dt.datetime.utcnow() - dt.timedelta(days=1)
    session = TrainingSession(
        user_id=user.id,
        status="finished",
        started_at=finished - dt.timedelta(hours=1),
        finished_at=finished,
        muscle_loads=muscle_loads,
    )
    db.session.add(session)
    db.session.flush()
    db.session.add(
        SessionExercise(
            session_id=session.id,
            exercise_id=catalog["bench-press"].id,
            sets_done=4,
            reps_done="8",
            rpe=8,
        )
    )
    db.session.commit()
    return session


def _rebuild_module():
    sys.path.insert(0, ROOT)
    from web.scripts import rebuild_muscle_loads

    return rebuild_muscle_loads


def test_rebuild_replaces_legacy_rows_and_leaves_valid_ones(app, user, catalog):
    legacy = _finished_session(user, catalog, {catalog["bench-press"].id: 480.0})
    emptied = _finished_session(user, catalog, {})
    valid = _finished_session(user, catalog, {"chest": 1.5})

    changed, total = _rebuild_module().rebuild()

    assert (changed, total) == (2, 3)
    db.session.refresh(legacy)
    db.session.refresh(emptied)
    db.session.refresh(valid)
    for rebuilt in (legacy, emptied):
        assert rebuilt.muscle_loads
        assert set(rebuilt.muscle_loads) <= known_muscle_slugs()
        assert rebuilt.muscle_loads["chest"] > 0
    assert valid.muscle_loads == {"chest": 1.5}


def test_rebuild_is_idempotent(app, user, catalog):
    _finished_session(user, catalog, {catalog["bench-press"].id: 480.0})
    module = _rebuild_module()
    module.rebuild()
    assert module.rebuild()[0] == 0
