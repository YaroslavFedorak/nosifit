"""Stimulus, fatigue cost, RPE mapping, contribution weights and novelty."""

import ast
import math
import pathlib

import pytest

from backend.app.services.training.model import parameters as P
from backend.app.services.training.model.stimulus import (
    contribution_weights,
    effective_rir,
    entry_dose,
    novelty_multiplier,
    set_fatigue_cost,
    set_stimulus,
)

from tm_helpers import entry

RIR_GRID = [r / 10 for r in range(0, 101)]


# --- parameter registry ------------------------------------------------------


def test_every_parameter_documents_its_evidence_level():
    assert P.REGISTRY
    for param in P.REGISTRY.values():
        assert param.name and param.unit and param.purpose and param.evidence
        assert param.confidence in {"high", "moderate", "low", "n/a"}
        assert isinstance(param.heuristic, bool)


@pytest.mark.parametrize(
    "name, heuristic",
    [
        ("DEFAULT_RIR", True),
        ("FATIGUE_HALF_LIFE_HOURS", True),
        ("READINESS_FATIGUE_SCALE", True),
        ("NOVELTY_MAX_MULTIPLIER", True),
        ("CONTRIBUTION_NORMALIZATION", True),
        ("SLEEP_MAX_READINESS_PENALTY", True),
        ("WEEKLY_SET_TARGETS", True),
        ("INDIRECT_SET_CAP", False),
        ("SLEEP_NEED_MINUTES", False),
    ],
)
def test_heuristics_are_labelled(name, heuristic):
    assert P.REGISTRY[name].heuristic is heuristic


def test_rpe_mapping_is_operational_not_high_confidence():
    assert P.REGISTRY["RPE_TO_RIR_OFFSET"].confidence != "high"


STRUCTURAL_CONSTANTS = {0, 1, 2, 3, 4, 7, 9, 100, 0.0, 0.5, 1.0, 2.0, 3.0, 7.0, 30.0, 3600.0, 86400.0}


def test_model_modules_have_no_unregistered_coefficients():
    """Coefficients live in parameters.py; other modules may only use
    structural constants (unit conversions, rounding digits, indices)."""
    root = pathlib.Path(P.__file__).parent
    for path in root.glob("*.py"):
        if path.name == "parameters.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        literals = {
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, (int, float))
            and not isinstance(node.value, bool)
        }
        assert literals <= STRUCTURAL_CONSTANTS, (path.name, literals - STRUCTURAL_CONSTANTS)


# --- RPE / RIR ----------------------------------------------------------------


@pytest.mark.parametrize("rpe, rir", [(10, 0), (9, 1), (8, 2), (7, 3), (5, 5), (1, 9)])
def test_rpe_maps_to_rir(rpe, rir):
    assert effective_rir(rpe) == (rir, True)


@pytest.mark.parametrize("rpe", [None, 0, -1, "abc", float("nan")])
def test_missing_or_invalid_rpe_uses_default(rpe):
    assert effective_rir(rpe) == (P.DEFAULT_RIR, False)


# --- stimulus and fatigue curves -------------------------------------------


def test_stimulus_is_normalised_at_failure_and_bounded():
    assert set_stimulus(0) == pytest.approx(1.0)
    for rir in RIR_GRID:
        assert 0.0 < set_stimulus(rir) <= 1.0


def test_stimulus_falls_monotonically_with_rir():
    values = [set_stimulus(r) for r in RIR_GRID]
    assert all(a > b for a, b in zip(values, values[1:]))


def test_stimulus_saturates_near_failure():
    assert set_stimulus(0) - set_stimulus(1) < 0.05
    assert set_stimulus(5) - set_stimulus(6) > set_stimulus(0) - set_stimulus(1)


def test_neighbouring_rir_values_never_jump():
    for rir in range(0, 10):
        assert abs(set_stimulus(rir) - set_stimulus(rir + 1)) < 0.15


def test_fatigue_falls_with_rir_and_never_below_stimulus():
    values = [set_fatigue_cost(r) for r in RIR_GRID]
    assert all(a > b for a, b in zip(values, values[1:]))
    for rir in RIR_GRID:
        assert set_fatigue_cost(rir) >= set_stimulus(rir)


def test_stimulus_to_fatigue_ratio_improves_away_from_failure():
    ratios = [set_stimulus(r) / set_fatigue_cost(r) for r in range(0, 7)]
    assert all(a < b for a, b in zip(ratios, ratios[1:]))
    assert ratios[0] == pytest.approx(0.5)  # failure: 2x fatigue per unit stimulus


# --- contribution weights ----------------------------------------------------


def test_profile_is_normalised_to_the_largest_share(catalog):
    weights = contribution_weights(catalog["bench-press"])
    assert weights["chest"] == pytest.approx(1.0)
    assert weights["triceps"] == pytest.approx(0.25 / 0.6)
    assert weights["shoulders"] == pytest.approx(0.15 / 0.6)


def test_secondary_muscles_are_capped(catalog):
    for exercise in catalog.values():
        for muscle, weight in contribution_weights(exercise).items():
            assert 0.0 < weight <= 1.0
            if muscle not in exercise.primary:
                assert weight <= P.INDIRECT_SET_CAP


def test_multiple_primary_muscles_keep_their_profile_ratio(catalog):
    weights = contribution_weights(catalog["barbell-back-squat"])
    assert weights["quads"] == pytest.approx(1.0)
    assert weights["glutes"] == pytest.approx(0.30 / 0.45)


def test_mobility_produces_no_stimulus_or_fatigue(catalog):
    mobility = next(x for x in catalog.values() if x.movement_pattern == "mobility")
    assert contribution_weights(mobility) == {}
    dose = entry_dose(entry(mobility.slug, 0, 3), mobility, None)
    assert dose.stimulus_sets == 0 and dose.fatigue_sets == 0


def test_bench_press_gives_indirect_triceps_and_shoulder_stimulus(catalog):
    dose = entry_dose(entry("bench-press", 0, 10, rpe=8), catalog["bench-press"], 3.0)
    muscles = dict(dose.muscle_stimulus)
    assert muscles["chest"] > muscles["triceps"] > muscles["shoulders"] > 0


# --- dose -------------------------------------------------------------------


def test_more_sets_never_reduce_stimulus(catalog):
    exercise = catalog["bench-press"]
    values = [entry_dose(entry("bench-press", 0, n), exercise, 3.0).stimulus_sets for n in range(0, 15)]
    assert all(a <= b for a, b in zip(values, values[1:]))


def test_load_and_reps_do_not_change_muscle_stimulus(catalog):
    exercise = catalog["bench-press"]
    light = entry_dose(entry("bench-press", 0, 3, reps=10, load=50), exercise, 3.0)
    heavy = entry_dose(entry("bench-press", 0, 3, reps=10, load=100), exercise, 3.0)
    assert light.muscle_stimulus == heavy.muscle_stimulus
    assert heavy.volume_load_kg == pytest.approx(2 * light.volume_load_kg)


def test_missing_reps_or_weight_still_counts_the_sets(catalog):
    exercise = catalog["push-ups"]
    dose = entry_dose(entry("push-ups", 0, 3, reps=None, rpe=None), exercise, None)
    assert dose.stimulus_sets == pytest.approx(3 * set_stimulus(P.DEFAULT_RIR))
    assert dose.volume_load_kg == 0.0


def test_duration_exercise_counts_sets(catalog):
    dose = entry_dose(entry("plank", 0, 3, reps=None, duration=45), catalog["plank"], 2.0)
    assert dose.stimulus_sets > 0


def test_bodyweight_tonnage_uses_bodyweight_ratio(catalog):
    exercise = catalog["push-ups"]
    dose = entry_dose(entry("push-ups", 0, 3, reps=10), exercise, 2.0, body_weight_kg=80)
    assert dose.volume_load_kg == pytest.approx(3 * 10 * 80 * exercise.bodyweight_ratio)


def test_heavy_sets_need_low_reps_close_to_failure(catalog):
    exercise = catalog["barbell-back-squat"]
    assert entry_dose(entry("barbell-back-squat", 0, 4, reps=5, rpe=9), exercise, 2.0).heavy_sets == 4
    assert entry_dose(entry("barbell-back-squat", 0, 4, reps=10, rpe=9), exercise, 2.0).heavy_sets == 0


# --- novelty -------------------------------------------------------------


def test_novelty_is_smooth_and_bounded():
    days = [d / 2 for d in range(0, 120)]
    values = [novelty_multiplier(d) for d in days]
    assert all(a <= b for a, b in zip(values, values[1:]))
    assert values[0] == 1.0
    assert novelty_multiplier(None) == P.NOVELTY_MAX_MULTIPLIER
    assert max(abs(a - b) for a, b in zip(values, values[1:])) < 0.02
    assert novelty_multiplier(P.NOVELTY_FAMILIAR_DAYS) == 1.0
    assert math.isclose(novelty_multiplier(P.NOVELTY_UNFAMILIAR_DAYS), P.NOVELTY_MAX_MULTIPLIER)


def test_novel_exercise_costs_more_fatigue_but_not_more_stimulus(catalog):
    exercise = catalog["bench-press"]
    familiar = entry_dose(entry("bench-press", 0, 4), exercise, 3.0)
    new = entry_dose(entry("bench-press", 0, 4), exercise, None)
    assert new.stimulus_sets == familiar.stimulus_sets
    assert new.fatigue_sets > familiar.fatigue_sets
