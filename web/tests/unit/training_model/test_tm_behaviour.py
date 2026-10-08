"""Behavioural, stability, sensitivity and invariant tests of the whole model.

These assert how recommendations should *behave* (direction, stability,
bounds), not specific numbers, so they do not pin the heuristic values.
"""

import random
from dataclasses import replace
from datetime import timedelta

import pytest

from backend.app.services.training.model import parameters as P
from backend.app.services.training.model.payload import recommendation_payload
from backend.app.services.training.model.priority import (
    allocate_sets,
    availability,
    focus_modifier,
    weak_modifier,
)
from backend.app.services.training.model.selection import target_rir
from backend.app.services.training.model.service import analyse

from tm_helpers import NOW, balanced_week, context, entry, nights


def run(catalog, entries, ctx=None, sleep=(), now=NOW):
    return analyse(ctx or context(), catalog, list(entries), list(sleep), now)


def plans(analysis):
    return {plan.muscle: plan for plan in analysis.plans}


def targets(analysis):
    return [plan.muscle for plan in analysis.plans if plan.targeted]


def main_targets(analysis):
    return [item.target_muscles[0] for item in analysis.exercises]


def history(weeks=5, sets=6, rpe=8.0):
    return [e for week in range(weeks) for e in balanced_week(week * 7, sets=sets, rpe=rpe)]


# --- edge cases -------------------------------------------------------------


def test_new_user_without_history(catalog):
    analysis = run(catalog, [])
    payload = recommendation_payload(analysis)
    assert payload["recommended_exercises"]
    assert payload["muscles"]["weak"] == []  # no "underloaded" without history
    assert all(s.readiness_level == "recovered" for s in analysis.statuses.values())
    assert all(s.insufficient_history for s in analysis.statuses.values())


def test_single_workout_lowers_readiness_of_trained_muscles_only(catalog):
    analysis = run(catalog, [entry("bench-press", 1, 8, rpe=9)])
    statuses = analysis.statuses
    assert statuses["chest"].readiness_score < statuses["quads"].readiness_score
    assert statuses["triceps"].readiness_score < 1.0  # indirect fatigue
    assert statuses["quads"].readiness_score == pytest.approx(1.0)


def test_very_large_workout_rests_the_muscle_and_avoids_it(catalog):
    analysis = run(catalog, [entry("bench-press", 0.5, 30, rpe=10)])
    assert plans(analysis)["chest"].action == "rest"
    assert "chest" in recommendation_payload(analysis)["muscles"]["overloaded"]
    assert "chest" not in main_targets(analysis)
    # Triceps get indirect fatigue from pressing and are not prioritised either.
    assert plans(analysis)["triceps"].action in ("rest", "reduce_volume")


def test_very_small_workout_changes_little(catalog):
    base = run(catalog, [])
    tiny = run(catalog, [entry("bench-press", 1, 1, rpe=6)])
    assert tiny.statuses["chest"].readiness_level == "recovered"
    assert abs(plans(base)["chest"].priority - plans(tiny)["chest"].priority) < 0.15


def test_many_hard_days_in_a_row_accumulate_fatigue(catalog):
    entries = [entry("barbell-back-squat", d, 6, rpe=10) for d in range(0, 5)]
    entries += [entry("leg-extension", d, 4, rpe=10) for d in range(0, 5)]
    analysis = run(catalog, entries)
    assert analysis.statuses["quads"].accumulated_fatigue
    assert plans(analysis)["quads"].action == "rest"
    assert recommendation_payload(analysis)["summary"].endswith("highLoad")


def test_long_break_clears_fatigue(catalog):
    old = [e for week in range(4) for e in balanced_week(60 + week * 7, sets=8, rpe=10)]
    analysis = run(catalog, old)
    for status in analysis.statuses.values():
        assert status.readiness_level == "recovered"
        assert status.fatigue < 0.01
        assert status.exposure_recent < 0.5


def test_uniform_load_within_band_flags_no_weak_muscle(catalog):
    analysis = run(catalog, history(sets=6), context(goal="general_fitness"))
    payload = recommendation_payload(analysis)
    for muscle, status in analysis.statuses.items():
        if status.major:
            assert status.exposure_smoothed >= status.lower_target, muscle
    assert payload["muscles"]["weak"] == []


def test_systematically_low_volume_is_underloaded(catalog):
    analysis = run(catalog, history(sets=2), context(goal="hypertrophy"))
    weak = recommendation_payload(analysis)["muscles"]["weak"]
    assert "chest" in weak and "quads" in weak


def test_bodyweight_isolation_and_compound_contributions(catalog):
    analysis = run(
        catalog,
        [entry("push-ups", 2, 4), entry("leg-extension", 2, 4), entry("barbell-back-squat", 2, 4)],
    )
    exposure = {m: s.exposure_recent for m, s in analysis.statuses.items()}
    assert exposure["chest"] > 0 and exposure["triceps"] > 0  # bodyweight compound
    assert exposure["quads"] > exposure["glutes"] > exposure["adductors"] > 0


def test_unknown_exercise_is_ignored(catalog):
    analysis = run(catalog, [entry("not-in-catalog", 1, 5)])
    assert analysis.doses == []


def test_beginner_only_gets_suitable_exercises(catalog):
    analysis = run(catalog, [], context(experience="beginner"))
    for item in analysis.exercises:
        assert item.exercise.difficulty <= P.MAX_DIFFICULTY["beginner"]
        assert item.exercise.risk_level <= P.MAX_RISK["beginner"]
        intermediate = target_rir(item.exercise, context(experience="intermediate"))
        assert item.target_rir == tuple(v + P.BEGINNER_EXTRA_RIR for v in intermediate)


def test_equipment_restriction_is_respected(catalog):
    analysis = run(catalog, [], context(available_equipment=frozenset({"bodyweight"})))
    assert analysis.exercises
    for item in analysis.exercises:
        assert set(item.exercise.equipment) <= {"bodyweight"}


def test_advanced_hypertrophy_gets_a_higher_band_than_beginner(catalog):
    beginner = run(catalog, [], context(experience="beginner"))
    advanced = run(catalog, [], context(experience="advanced"))
    assert advanced.statuses["chest"].lower_target > beginner.statuses["chest"].lower_target
    assert plans(advanced)["chest"].allocated_sets >= plans(beginner)["chest"].allocated_sets


def test_strength_goal_prescribes_low_reps_on_loaded_compounds(catalog):
    analysis = run(catalog, [], context(goal="strength"))
    loaded = [i for i in analysis.exercises if i.exercise.load_type in ("external", "machine", "cable")
              and i.exercise.movement_pattern not in ("isolation",)]
    assert loaded
    assert all(i.reps == "3-6" for i in loaded if i.reps is not None)


def test_goals_share_physiology_but_differ_in_policy(catalog):
    entries = history(sets=4)
    hyp = run(catalog, entries, context(goal="hypertrophy"))
    fat = run(catalog, entries, context(goal="fat_loss"))
    for muscle in ("chest", "quads"):
        assert hyp.statuses[muscle].readiness_score == fat.statuses[muscle].readiness_score
        assert hyp.statuses[muscle].exposure_recent == fat.statuses[muscle].exposure_recent
    assert hyp.statuses["chest"].lower_target > fat.statuses["chest"].lower_target


# --- weak points and focus ---------------------------------------------------


def test_weak_point_raises_priority_but_never_bypasses_readiness(catalog):
    fatigued = [entry("pull-ups", 0.5, 12, rpe=10), entry("barbell-row", 0.5, 8, rpe=10)]
    plain = run(catalog, fatigued)
    weak = run(catalog, fatigued, context(weak_muscles=frozenset({"lats"})))
    assert plans(weak)["lats"].priority == plans(plain)["lats"].priority == 0.0
    assert "lats" not in targets(weak)

    fresh_plain = run(catalog, [])
    fresh_weak = run(catalog, [], context(weak_muscles=frozenset({"lats"})))
    assert plans(fresh_weak)["lats"].priority > plans(fresh_plain)["lats"].priority


@pytest.mark.parametrize(
    "focus, weak, expected",
    [(5, False, 1.0), (10, False, 1.5), (0, False, 0.5), (0, True, 1.0), (10, True, 1.5), (None, False, 1.0)],
)
def test_focus_modifier_rules(focus, weak, expected):
    assert focus_modifier(focus, weak) == pytest.approx(expected)


def test_weak_point_outweighs_low_focus(catalog):
    ctx = context(weak_muscles=frozenset({"chest"}), focus={"chest": 0})
    plan = plans(run(catalog, [], ctx))["chest"]
    assert plan.weak_modifier * plan.focus_modifier >= weak_modifier(True)


# --- sleep -------------------------------------------------------------------


@pytest.mark.parametrize("bad_nights", [1, 3, 7])
def test_bad_sleep_never_increases_volume(catalog, bad_nights):
    entries = history(sets=4)
    rested = run(catalog, entries)
    tired = run(catalog, entries, sleep=nights({i: 300 for i in range(bad_nights)}))
    for muscle, plan in plans(tired).items():
        assert plan.allocated_sets <= plans(rested)[muscle].allocated_sets
        assert tired.statuses[muscle].readiness_score <= rested.statuses[muscle].readiness_score
        # Sleep never changes stimulus history.
        assert tired.statuses[muscle].exposure_recent == rested.statuses[muscle].exposure_recent


def test_one_bad_night_does_not_make_a_recovered_muscle_unavailable(catalog):
    analysis = run(catalog, [], sleep=nights({0: 240}))
    assert all(s.readiness_level in ("recovered", "ready") for s in analysis.statuses.values())


# --- stability ---------------------------------------------------------------


def test_same_history_gives_identical_output(catalog):
    entries = history(sets=5)
    first = recommendation_payload(run(catalog, entries))
    shuffled = list(entries)
    random.Random(7).shuffle(shuffled)
    second = recommendation_payload(run(catalog, shuffled))
    assert first == second


def test_one_extra_set_yesterday_is_a_small_predictable_change(catalog):
    entries = history(sets=4)
    base = run(catalog, entries)
    more = run(catalog, entries + [entry("bench-press", 1, 1, rpe=8, session=999)])
    assert more.statuses["chest"].exposure_recent > base.statuses["chest"].exposure_recent
    assert more.statuses["chest"].readiness_score <= base.statuses["chest"].readiness_score
    assert abs(plans(more)["chest"].allocated_sets - plans(base)["chest"].allocated_sets) <= 1
    for muscle in ("quads", "hamstrings", "lats", "calves"):
        assert plans(more)[muscle].priority == pytest.approx(plans(base)[muscle].priority)
    assert len(set(targets(more)) & set(targets(base))) >= len(targets(base)) - 1


def test_one_more_rir_is_a_small_predictable_change(catalog):
    hard = run(catalog, history(sets=4, rpe=8))
    easier = run(catalog, history(sets=4, rpe=7))
    for muscle in ("chest", "quads"):
        assert easier.statuses[muscle].exposure_recent < hard.statuses[muscle].exposure_recent
        assert easier.statuses[muscle].readiness_score >= hard.statuses[muscle].readiness_score
        ratio = easier.statuses[muscle].exposure_recent / hard.statuses[muscle].exposure_recent
        assert 0.85 < ratio < 1.0


def test_old_session_leaving_the_window_causes_no_collapse(catalog):
    entries = [entry("bench-press", 14, 8, session=1), entry("bench-press", 28, 8, session=2)]
    for hours in range(-12, 13, 3):
        moment = NOW + timedelta(hours=hours)
        a = run(catalog, entries, now=moment)
        b = run(catalog, entries, now=moment + timedelta(hours=3))
        assert abs(a.statuses["chest"].exposure_recent - b.statuses["chest"].exposure_recent) < 0.2
        assert abs(a.statuses["chest"].exposure_long - b.statuses["chest"].exposure_long) < 0.2
        assert abs(plans(a)["chest"].priority - plans(b)["chest"].priority) < 0.05


def test_small_change_in_one_muscle_does_not_reorder_the_others(catalog):
    entries = history(sets=4)
    base = run(catalog, entries)
    changed = run(catalog, entries + [entry("barbell-curl", 3, 2, rpe=8, session=998)])

    def order(analysis):
        return [p.muscle for p in analysis.plans if p.muscle not in ("biceps", "forearms")]

    assert order(base) == order(changed)


def test_states_do_not_flap_day_to_day_under_a_steady_routine(catalog):
    entries = [e for week in range(8) for e in balanced_week(week * 7 - 7, sets=6)]
    zones = []
    for day in range(0, 14):
        analysis = run(catalog, entries, context(goal="general_fitness"), now=NOW + timedelta(days=day - 7))
        zones.append(analysis.statuses["chest"].volume_zone)
    changes = sum(1 for a, b in zip(zones, zones[1:]) if a != b)
    assert changes <= 1


# --- sensitivity to heuristic scales -------------------------------------


@pytest.mark.parametrize("name, values", [
    ("READINESS_FATIGUE_SCALE", (6.0, 8.0, 10.0)),
    ("FATIGUE_HALF_LIFE_HOURS", (24.0, 30.0, 36.0)),
])
def test_recommendations_are_robust_to_heuristic_scales(catalog, monkeypatch, name, values):
    entries = history(sets=4) + [entry("bench-press", 1, 6, rpe=9, session=997)]
    results = []
    for value in values:
        monkeypatch.setattr(P, name, value)
        results.append(targets(run(catalog, entries)))
    first = set(results[0])
    for other in results[1:]:
        assert len(first & set(other)) >= len(first) - 1


# --- invariants ------------------------------------------------------------


@pytest.mark.parametrize("sets", [0, 1, 3, 6, 12])
@pytest.mark.parametrize("rpe", [None, 6, 8, 10])
def test_invariants(catalog, sets, rpe):
    analysis = run(catalog, [entry("bench-press", 1, sets, rpe=rpe), entry("barbell-back-squat", 2, sets, rpe=rpe)])
    max_priority = (1 + P.WEAK_POINT_BONUS) * (1 + P.FOCUS_MAX_ADJUSTMENT)
    for status in analysis.statuses.values():
        assert status.fatigue >= 0
        assert status.exposure_recent >= 0 and status.exposure_long >= 0
        assert 0.0 <= status.readiness_score <= 1.0
    for plan in analysis.plans:
        assert 0.0 <= plan.priority <= max_priority
        assert 0 <= plan.allocated_sets <= P.SESSION_SET_CAP_PER_MUSCLE
    for item in analysis.exercises:
        assert P.MIN_SESSION_SETS <= item.sets <= P.MAX_SETS_PER_EXERCISE


@pytest.mark.parametrize("sets", [2, 4, 6, 8, 10, 12, 16])
def test_more_recent_load_never_improves_readiness(catalog, sets):
    lighter = run(catalog, [entry("bench-press", 1, sets, rpe=8)])
    heavier = run(catalog, [entry("bench-press", 1, sets + 2, rpe=8)])
    assert heavier.statuses["chest"].readiness_score <= lighter.statuses["chest"].readiness_score
    assert plans(heavier)["chest"].allocated_sets <= plans(lighter)["chest"].allocated_sets


def test_lower_readiness_never_allocates_more_sets():
    values = [allocate_sets(4.0, 10, 16, 2, availability(r / 100)) for r in range(0, 101)]
    assert all(a <= b for a, b in zip(values, values[1:]))


def test_repeated_workout_behaves_consistently(catalog):
    once = run(catalog, [entry("bench-press", 3, 5, session=1)])
    twice = run(catalog, [entry("bench-press", 3, 5, session=1), entry("bench-press", 1, 5, session=2)])
    assert twice.statuses["chest"].exposure_recent > once.statuses["chest"].exposure_recent
    assert twice.statuses["triceps"].exposure_recent > once.statuses["triceps"].exposure_recent
    assert twice.statuses["chest"].readiness_score < once.statuses["chest"].readiness_score


@pytest.mark.parametrize("goal", sorted(P.WEEKLY_SET_TARGETS))
@pytest.mark.parametrize("experience", ["beginner", "intermediate", "advanced"])
@pytest.mark.parametrize("workouts", [1, 3, 6])
def test_every_profile_gets_recommendations(catalog, goal, experience, workouts):
    """Regression: small weekly bands split over many sessions used to round
    every allocation below the minimum and return nothing."""
    ctx = context(goal=goal, experience=experience, workouts_per_week=workouts)
    analysis = run(catalog, [], ctx)
    assert analysis.exercises
    assert all(plan.allocated_sets >= P.MIN_SESSION_SETS for plan in analysis.plans if plan.targeted)
