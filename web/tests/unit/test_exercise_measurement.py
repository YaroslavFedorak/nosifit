from types import SimpleNamespace

import pytest

from backend.app.services.training.load.exercise import calculate_measured_load
from backend.app.services.training.load.service import TrainingLoadService
from backend.app.training.exercises.catalog import load_exercise_catalog
from backend.app.training.exercises.prescription import (
    build_entry,
    default_entry,
    format_entry,
    performed_values,
    session_update_fields,
)
from backend.app.training.models.training_day import TrainingDay
from backend.app.training.training_analysis.analyzers.muscles import _exercise_load


@pytest.fixture(scope="module")
def exercises():
    return {
        item["slug"]: SimpleNamespace(id=item["slug"], **item)
        for item in load_exercise_catalog()
    }


def test_push_up_is_prescribed_in_reps(exercises):
    push_up = exercises["push-ups"]

    entry = build_entry(push_up, sets=3, reps=12)

    assert entry["measurement_type"] == "reps"
    assert entry["reps"] == 12
    assert entry["duration_sec"] is None
    assert format_entry(entry) == "3 × 12"


def test_push_up_default_prescription_uses_rep_range(exercises):
    entry = default_entry(exercises["push-ups"])

    assert entry == {"sets": 3, "reps": "8-20", "duration_sec": None, "per_side": False}


def test_push_up_load_scales_with_reps_and_weight(exercises):
    push_up = exercises["push-ups"]

    light = calculate_measured_load(push_up, user_weight=80, sets=3, reps=8)
    heavy = calculate_measured_load(push_up, user_weight=80, sets=3, reps=15)
    weighted = calculate_measured_load(
        push_up, user_weight=80, sets=3, reps=8, additional_weight=20
    )

    assert light["measurement_type"] == "reps"
    assert 0 < light["internal_load"] < heavy["internal_load"]
    assert weighted["internal_load"] > light["internal_load"]
    assert light["load"] == pytest.approx(80 * push_up.bodyweight_ratio)


def test_plank_is_prescribed_in_seconds(exercises):
    plank = exercises["plank"]

    entry = build_entry(plank, sets=3, duration_sec=45)

    assert entry["measurement_type"] == "duration"
    assert entry["duration_sec"] == 45
    assert entry["reps"] is None
    assert format_entry(entry) == "3 × 45 sec"
    assert default_entry(plank) == {
        "sets": 3,
        "reps": None,
        "duration_sec": 55,
        "per_side": False,
    }


def test_plank_load_ignores_repetitions(exercises):
    plank = exercises["plank"]

    by_seconds = calculate_measured_load(
        plank, user_weight=80, sets=3, duration_sec=45
    )
    with_bogus_reps = calculate_measured_load(
        plank, user_weight=80, sets=3, reps=999, duration_sec=45
    )
    reps_only = calculate_measured_load(plank, user_weight=80, sets=3, reps=45)
    longer = calculate_measured_load(plank, user_weight=80, sets=3, duration_sec=90)

    assert by_seconds["measurement_type"] == "duration"
    assert by_seconds["seconds"] == 45
    assert "reps" not in by_seconds
    assert by_seconds["internal_load"] > 0
    assert with_bogus_reps["internal_load"] == by_seconds["internal_load"]
    assert reps_only["internal_load"] == 0
    assert longer["internal_load"] > by_seconds["internal_load"]


def test_measurement_type_comes_from_data_not_names():
    # A made-up exercise named like a plank but declared as reps must be
    # treated as reps; nothing in the engine keys off names or slugs.
    fake = SimpleNamespace(
        slug="plank-to-push-up",
        name="Plank to Push-Up",
        measurement_type="reps",
        movement_pattern="push",
        load_type="bodyweight",
        bodyweight_ratio=0.6,
        difficulty=2,
        risk_level=1,
        equipment=["bodyweight"],
        max_additional_load_kg=None,
        prescription={"sets": 3, "reps_min": 6, "reps_max": 12},
    )

    result = calculate_measured_load(fake, user_weight=80, sets=3, reps=10)

    assert result["measurement_type"] == "reps"
    assert result["internal_load"] > 0


def test_session_service_reads_done_columns(exercises):
    plank_row = SimpleNamespace(
        sets_done=3,
        sets_planned=None,
        reps_done=None,
        reps_planned=None,
        duration_sec_done=45,
        duration_sec_planned=None,
        load_done=None,
        load_planned=None,
        rpe=None,
    )

    result = TrainingLoadService.compute_exercise_load(
        plank_row, exercises["plank"], capacity={"weight": 80}
    )

    assert result["measurement_type"] == "duration"
    assert result["internal_load"] > 0


def test_performed_values_keep_measurements_apart(exercises):
    row = SimpleNamespace(
        sets_done=2,
        reps_done="12",
        duration_sec_done=30,
        load_done=0,
    )

    assert performed_values(row, exercises["dead-hang"]) == {
        "measurement_type": "duration",
        "sets": 2,
        "reps": None,
        "duration_sec": 30,
        "load": 0.0,
    }
    assert performed_values(row, exercises["push-ups"])["duration_sec"] is None
    assert performed_values(row, exercises["push-ups"])["reps"] == 12


def test_session_payload_mapping(exercises):
    plank_fields = session_update_fields(
        exercises["plank"], {"sets": 3, "duration_sec": 45, "load": 0}
    )
    push_fields = session_update_fields(
        exercises["push-ups"], {"sets": 3, "reps": 12, "duration_sec": 45}
    )

    # Values sent without per-set entries clear stored sets, which would no
    # longer match them (set_entries, PR #23).
    assert plank_fields == {
        "sets_done": 3,
        "load_done": 0,
        "duration_sec_done": 45,
        "reps_done": None,
        "set_entries": None,
    }
    assert push_fields == {
        "sets_done": 3,
        "reps_done": "12",
        "duration_sec_done": None,
        "set_entries": None,
    }


def test_reps_are_never_read_as_seconds(exercises):
    fields = session_update_fields(exercises["wall-sit"], {"sets": 3, "reps": "60"})

    assert "duration_sec_done" not in fields
    assert "reps_done" not in fields


def test_seconds_are_never_read_as_reps(exercises):
    fields = session_update_fields(
        exercises["push-ups"], {"sets": 3, "duration_sec": 45}
    )

    assert "reps_done" not in fields
    assert "duration_sec_done" not in fields


def test_muscle_analytics_load_uses_each_exercise_own_unit(exercises):
    plank = exercises["plank"]
    push_up = exercises["push-ups"]

    plank_45 = _exercise_load(
        SimpleNamespace(sets_done=3, duration_sec_done=45), plank, 80
    )
    plank_45_with_reps = _exercise_load(
        SimpleNamespace(sets_done=3, duration_sec_done=45, reps_done="99"), plank, 80
    )
    plank_reps_only = _exercise_load(
        SimpleNamespace(sets_done=3, reps_done="45"), plank, 80
    )
    push_12 = _exercise_load(SimpleNamespace(sets_done=3, reps_done="12"), push_up, 80)
    push_12_with_seconds = _exercise_load(
        SimpleNamespace(sets_done=3, reps_done="12", duration_sec_done=99), push_up, 80
    )

    assert plank_45 > 0
    assert plank_45_with_reps == plank_45
    assert plank_reps_only == 0
    assert push_12 > 0
    assert push_12_with_seconds == push_12


def test_constants_have_no_rep_seconds_conversion():
    from backend.app.services.training.load import constants

    assert not hasattr(constants, "SECONDS_PER_REP_EQUIVALENT")


def test_per_side_is_kept_in_prescriptions(exercises):
    lunge = build_entry(exercises["bulgarian-split-squat"], sets=3, reps=10)
    side_plank = build_entry(exercises["side-plank"], sets=3, duration_sec=30)
    push_up = build_entry(exercises["push-ups"], sets=3, reps=10)

    assert lunge["per_side"] is True
    assert side_plank["per_side"] is True
    assert push_up["per_side"] is False
    assert format_entry(lunge) == "3 × 10 / side"
    assert format_entry(side_plank) == "3 × 30 sec / side"
    assert format_entry(push_up) == "3 × 10"
    assert default_entry(exercises["side-plank"])["per_side"] is True


def test_mixed_training_day_serializes(exercises):
    day = TrainingDay(day_name="mon", name="Mixed")
    day.add_exercise(exercises["push-ups"], sets=3, reps=12)
    day.add_exercise(exercises["plank"], sets=3, duration_sec=45)
    day.add_exercise(exercises["barbell-back-squat"], sets=3, reps=10, load=60)
    day.add_exercise(exercises["dead-hang"], sets=2, duration_sec=30)

    serialized = day.to_dict()["exercises"]

    assert [format_entry(item) for item in serialized] == [
        "3 × 12",
        "3 × 45 sec",
        "3 × 10",
        "2 × 30 sec",
    ]
    assert serialized[1]["reps"] is None
    assert serialized[3]["reps"] is None
    assert serialized[0]["duration_sec"] is None
    assert serialized[2]["load"] == 60.0
