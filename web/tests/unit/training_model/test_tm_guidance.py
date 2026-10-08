""""What to train today and why" (model/guidance.py).

Two layers:
* status-level tests build MuscleStatus values directly, run the real Stage 1
  (plan_muscles) and read the guidance, so every volume zone, readiness level
  and focus case is exact;
* pipeline tests run the whole model on logged workouts.
"""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.app.services.training.model import parameters as P
from backend.app.services.training.model.context import (
    GOAL_ALIASES,
    GOALS,
    focus_by_muscle,
    normalize_goal,
)
from backend.app.services.training.model.guidance import build_guidance
from backend.app.services.training.model.payload import guidance_payload, recommendation_payload
from backend.app.services.training.model.priority import plan_muscles
from backend.app.services.training.model.service import analyse
from backend.app.services.training.model.status import MuscleStatus, weekly_targets

from tm_helpers import NOW, balanced_week, context, entry

# Readiness scores inside each level (bounds 0.45 / 0.65 / 0.85).
LEVEL_SCORE = {"low": 0.30, "moderate": 0.55, "ready": 0.75, "recovered": 0.95}
TRANSLATIONS = Path(__file__).resolve().parents[3] / "app" / "translations"
LANGUAGES = ("uk", "en", "pl", "ru")


def status(muscle, sets, ctx, level="recovered", underloaded=False, accumulated=False, days=3.0):
    lower, upper = weekly_targets(ctx)
    zone = "below" if sets < lower else "above" if sets > upper else "within"
    return MuscleStatus(
        muscle=muscle,
        major=True,
        exposure_recent=sets,
        exposure_smoothed=sets,
        exposure_long=sets,
        trend="stable",
        fatigue=0.0,
        readiness_score=LEVEL_SCORE[level],
        readiness_level=level,
        sleep_modifier=1.0,
        lower_target=float(lower),
        upper_target=float(upper),
        volume_zone=zone,
        below_target=zone == "below",
        underloaded=underloaded,
        high_volume=zone == "above",
        accumulated_fatigue=accumulated,
        insufficient_history=False,
        days_since_trained=days,
        state="appropriate",
    )


def middle(ctx):
    lower, upper = weekly_targets(ctx)
    return (lower + upper) / 2.0


def statuses(ctx, overrides=None, default=None):
    """Every major muscle at the band middle (nothing to do) unless overridden.
    ``overrides``: {muscle: sets} or {muscle: (sets, {status kwargs})}."""
    base = middle(ctx) if default is None else default
    result = {m: status(m, base, ctx) for m in P.MAJOR_MUSCLES}
    for muscle, value in (overrides or {}).items():
        sets, extra = value if isinstance(value, tuple) else (value, {})
        result[muscle] = status(muscle, sets, ctx, **extra)
    return result


def guide(ctx, overrides=None, default=None):
    current = statuses(ctx, overrides, default)
    return build_guidance(plan_muscles(current, ctx), current, has_history=True)


def by_muscle(guidance):
    return {item.muscle: item for item in guidance.muscles + guidance.warnings}


def short(keys):
    return [key.rsplit(".", 1)[-1] for key in keys]


CTX = context()  # hypertrophy / intermediate: band 10-16, middle 13


# --- volume zones -----------------------------------------------------------


def test_under_target_muscle_is_the_priority():
    g = guide(CTX, {"quads": 4})
    assert g.verdict == "focus"
    assert [i.muscle for i in g.muscles] == ["quads"]
    quads = g.muscles[0]
    assert quads.kind == "priority"
    assert short(quads.reasons)[0] == "belowTarget"
    assert quads.suggested_sets >= P.MIN_SESSION_SETS


def test_within_target_is_supporting_not_priority():
    g = guide(CTX, default=11)  # 10 <= 11 <= 16, below the middle
    assert g.verdict == "train"
    assert g.muscles and all(i.kind == "train" for i in g.muscles)
    assert all("withinTarget" in short(i.reasons) for i in g.muscles)
    assert not g.warnings


def test_above_target_never_gets_more_volume():
    g = guide(CTX, {"chest": 18, "quads": 4})
    chest = by_muscle(g)["chest"]
    assert chest.kind == "enough"
    assert chest.suggested_sets == 0
    assert "chest" not in [i.muscle for i in g.muscles]
    assert short(chest.reasons) == ["highVolume"]


def test_everything_at_target_is_balanced_without_inventing_a_muscle():
    g = guide(CTX)
    assert g.verdict == "balanced"
    assert g.muscles == () and g.warnings == ()


@pytest.mark.parametrize(
    "sets, kind",
    [(9.5, "priority"), (10.0, "train"), (10.5, "train"), (16.0, "train"), (16.5, "enough")],
)
def test_fractional_sets_respect_the_band_bounds(sets, kind):
    g = guide(CTX, {"quads": sets})
    item = by_muscle(g).get("quads")
    if sets == 16.0:
        # Within the band but above the middle: nothing to add, nothing to warn.
        assert item is None
    else:
        assert item.kind == kind


def test_lower_bound_not_the_middle_decides_priority():
    # 11 sets is below the middle (13) but within the band: supporting only.
    g = guide(CTX, {"quads": 11, "chest": 9})
    kinds = {i.muscle: i.kind for i in g.muscles}
    assert kinds == {"chest": "priority", "quads": "train"}
    assert [i.muscle for i in g.muscles][0] == "chest"


# --- recovery ---------------------------------------------------------------


@pytest.mark.parametrize(
    "level, kind, first_reason",
    [
        ("low", "rest", "lowReadiness"),
        ("moderate", "reduce", "moderateReadiness"),
        ("ready", "priority", "belowTarget"),
        ("recovered", "priority", "belowTarget"),
    ],
)
def test_readiness_level_shapes_the_recommendation(level, kind, first_reason):
    g = guide(CTX, {"quads": (4, {"level": level})})
    item = by_muscle(g)["quads"]
    assert item.kind == kind
    assert short(item.reasons)[0] == first_reason
    if kind in ("rest", "reduce"):
        assert item.suggested_sets == 0
        assert "quads" not in [i.muscle for i in g.muscles]
    if level in ("ready", "recovered"):
        assert level in short(item.reasons)


def test_low_readiness_shows_only_the_recovery_reason():
    g = guide(CTX, {"quads": (4, {"level": "low", "underloaded": True})})
    assert short(by_muscle(g)["quads"].reasons) == ["lowReadiness"]


def test_moderate_readiness_keeps_the_volume_reason():
    g = guide(CTX, {"quads": (4, {"level": "moderate"})})
    assert short(by_muscle(g)["quads"].reasons) == ["moderateReadiness", "belowTarget"]


def test_underloaded_muscle_never_outranks_readiness():
    g = guide(CTX, {"quads": (2, {"level": "low", "underloaded": True}), "chest": 9})
    assert [i.muscle for i in g.muscles] == ["chest"]
    assert by_muscle(g)["quads"].kind == "rest"


# --- fatigue ----------------------------------------------------------------


def test_accumulated_fatigue_means_rest():
    g = guide(CTX, {"chest": (4, {"level": "moderate", "accumulated": True})})
    chest = by_muscle(g)["chest"]
    assert chest.kind == "rest"
    assert short(chest.reasons) == ["accumulatedFatigue"]
    assert g.accumulated_fatigue


def _analysis(current, doses=(object(),)):
    return SimpleNamespace(plans=plan_muscles(current, CTX), statuses=current, doses=list(doses))


def test_rest_day_when_no_muscle_is_ready():
    tired = {m: (13, {"level": "moderate", "accumulated": m in ("chest", "quads")}) for m in P.MAJOR_MUSCLES}
    current = statuses(CTX, tired)
    payload = guidance_payload(_analysis(current))
    assert payload["verdict"] == "rest"
    assert payload["message"].endswith("verdict.rest.messageFatigue")
    assert payload["muscles"] == []


def test_rest_day_without_accumulated_fatigue_uses_the_plain_message():
    current = statuses(CTX, {m: (13, {"level": "moderate"}) for m in P.MAJOR_MUSCLES})
    payload = guidance_payload(_analysis(current))
    assert payload["verdict"] == "rest"
    assert payload["message"].endswith("verdict.rest.message")


def test_no_accumulated_fatigue_no_warning():
    g = guide(CTX, {"quads": 4})
    assert not g.accumulated_fatigue
    assert not any(i.kind == "rest" for i in g.warnings)


def test_trainable_muscles_beat_a_rest_day():
    # Local fatigue in one muscle does not turn the whole day into rest.
    g = guide(CTX, {"chest": (4, {"level": "low", "accumulated": True}), "quads": 4})
    assert g.verdict == "focus"
    assert [i.muscle for i in g.muscles] == ["quads"]
    assert by_muscle(g)["chest"].kind == "rest"


@pytest.mark.parametrize("others", [11, None])  # something to add / already at target
def test_one_tired_muscle_never_makes_the_whole_day_rest(others):
    tired = {"quads": (4, {"level": "low", "accumulated": True})}
    payload = guidance_payload(_analysis(statuses(CTX, tired, default=others)))
    assert payload["verdict"] != "rest"
    assert payload["verdict"] == ("train" if others else "balanced")
    assert not payload["message"].endswith("messageFatigue")
    assert [i["muscle"] for i in payload["warnings"]] == ["quads"]
    assert payload["warnings"][0]["kind"] == "rest"


def test_several_tired_muscles_with_ready_others_are_not_a_rest_day():
    tired = {m: (13, {"level": "low", "accumulated": True}) for m in ("quads", "glutes", "hamstrings", "chest")}
    payload = guidance_payload(_analysis(statuses(CTX, tired)))
    assert payload["verdict"] == "balanced"
    assert len(payload["warnings"]) == P.GUIDANCE_MAX_WARNINGS


# --- no_history is about history, not about having a recommendation -------


def test_no_history_depends_on_history_not_on_recommendations():
    current = statuses(CTX)  # nothing to recommend either way
    assert guidance_payload(_analysis(current, doses=()))["verdict"] == "no_history"
    with_history = guidance_payload(_analysis(current))
    assert with_history["verdict"] == "balanced"
    assert with_history["title"].endswith("verdict.balanced.title")


def test_user_with_history_and_even_volume_gets_balanced_not_new_user(catalog):
    routine = (
        (2, (("bench-press", 3, 8, 60), ("barbell-row", 3, 10, 50), ("barbell-back-squat", 3, 6, 80),
             ("hanging-leg-raise", 3, 12, 0))),
        (4, (("overhead-press", 3, 8, 35), ("pull-ups", 3, 8, 0), ("romanian-deadlift", 3, 10, 60),
             ("calf-raise", 3, 15, 0))),
        (6, (("barbell-curl", 3, 12, 25), ("tricep-pushdown", 3, 12, 25), ("calf-raise", 3, 15, 0),
             ("hanging-leg-raise", 3, 12, 0), ("leg-curl", 2, 12, 30))),
    )
    entries = [
        entry(slug, week * 7 + day, sets, reps, 8.0, load, session=week * 10 + day)
        for week in range(5)
        for day, items in routine
        for slug, sets, reps, load in items
    ]
    guidance = recommendation_payload(run(catalog, entries, context(goal="maintenance")))["guidance"]
    assert guidance["verdict"] == "balanced"
    assert guidance["muscles"] == []


# --- focus ------------------------------------------------------------------


@pytest.mark.parametrize(
    "focus, pair, expected_first",
    [
        ({}, ("chest", "hamstrings"), "chest"),  # tie-break order only
        ({"upper": 9}, ("quads", "chest"), "chest"),
        ({"lower": 9}, ("chest", "hamstrings"), "hamstrings"),
        ({"core": 9}, ("chest", "abs"), "abs"),
    ],
)
def test_focus_breaks_an_equal_deficit(focus, pair, expected_first):
    ctx = context(focus=focus_by_muscle(**focus))
    g = guide(ctx, {pair[0]: 6, pair[1]: 6})
    assert [i.muscle for i in g.muscles][0] == expected_first
    assert {i.muscle for i in g.muscles} == set(pair)


def test_upper_focus_shows_as_a_reason():
    ctx = context(focus=focus_by_muscle(upper=9))
    g = guide(ctx, {"chest": 6})
    assert short(by_muscle(g)["chest"].reasons) == ["belowTarget", "focus"]


def test_focus_never_bypasses_readiness():
    ctx = context(focus=focus_by_muscle(upper=10))
    g = guide(ctx, {"chest": (4, {"level": "low"}), "quads": 6})
    assert [i.muscle for i in g.muscles] == ["quads"]
    assert by_muscle(g)["chest"].kind == "rest"


def test_focus_does_not_create_a_priority_without_a_deficit():
    ctx = context(focus=focus_by_muscle(upper=10))
    assert guide(ctx).verdict == "balanced"


# --- goal -------------------------------------------------------------------


@pytest.mark.parametrize("alias", sorted(GOAL_ALIASES))
def test_every_goal_alias_is_canonical(alias):
    assert normalize_goal(alias) in GOALS


@pytest.mark.parametrize(
    "raw, kind",
    [
        ("gain", "priority"),  # hypertrophy intermediate 10-16: 9 is below
        ("muscle_gain", "priority"),
        ("recomposition", "priority"),
        ("maintain", "enough"),  # maintenance 3-6: 9 is above
        ("maintenance", "enough"),
        ("lose", None),  # fat_loss 4-10: 9 is within, above the middle
        ("strength", None),
        ("performance", None),
        ("endurance", None),
    ],
)
def test_bands_follow_the_canonical_goal(raw, kind):
    ctx = context(goal=normalize_goal(raw))
    item = by_muscle(guide(ctx, {"quads": 9}, default=middle(ctx))).get("quads")
    assert (item.kind if item else None) == kind


# --- ties, determinism, limits ---------------------------------------------


def test_many_equal_priorities_are_capped_and_deterministic():
    deficits = {m: 4 for m in P.MAJOR_MUSCLES}
    first = guide(CTX, deficits)
    second = guide(CTX, deficits)
    assert first == second
    assert len(first.muscles) == P.GUIDANCE_MAX_MUSCLES
    assert [i.muscle for i in first.muscles] == list(P.STAGE1_TIE_BREAK_ORDER[: P.GUIDANCE_MAX_MUSCLES])


def test_warnings_are_capped_and_rest_comes_first():
    over = {m: 18 for m in P.MAJOR_MUSCLES}
    over["calves"] = (13, {"level": "low"})
    g = guide(CTX, over)
    assert len(g.warnings) == P.GUIDANCE_MAX_WARNINGS
    assert g.warnings[0].muscle == "calves" and g.warnings[0].kind == "rest"


# --- whole pipeline ---------------------------------------------------------


def run(catalog, entries, ctx=None):
    return analyse(ctx or context(), catalog, list(entries), [], NOW)


def test_new_user_gets_no_invented_priority(catalog):
    payload = recommendation_payload(run(catalog, []))
    guidance = payload["guidance"]
    assert guidance["verdict"] == "no_history"
    assert guidance["muscles"] == [] and guidance["warnings"] == []
    assert guidance["title"].endswith("verdict.no_history.title")
    assert payload["recommended_exercises"]  # exercise selection is separate


def test_skipped_legs_become_the_priority(catalog):
    upper = [
        e
        for week in range(5)
        for e in (
            entry("bench-press", week * 7 + 2, 5, 8, 8, 60),
            entry("barbell-row", week * 7 + 2, 5, 10, 8, 50),
            entry("overhead-press", week * 7 + 4, 5, 8, 8, 35),
            entry("pull-ups", week * 7 + 4, 5, 8, 8),
        )
    ]
    guidance = recommendation_payload(run(catalog, upper))["guidance"]
    assert guidance["verdict"] == "focus"
    legs = {"quads", "hamstrings", "glutes", "calves"}
    assert {i["muscle"] for i in guidance["muscles"]} <= legs | {"abs", "biceps", "triceps"}
    assert guidance["muscles"][0]["muscle"] in legs
    assert any(r.endswith("undertrained") for r in guidance["muscles"][0]["reasons"])


def test_hammered_muscles_are_held_back(catalog):
    heavy = [entry("barbell-back-squat", d, 8, 6, 9.5, 100) for d in (0.2, 1, 2, 3)]
    heavy += [entry("bench-press", d, 8, 6, 9.5, 80) for d in (0.2, 1, 2, 3)]
    guidance = recommendation_payload(run(catalog, heavy))["guidance"]
    held = {i["muscle"]: i["kind"] for i in guidance["warnings"]}
    trained = {i["muscle"] for i in guidance["muscles"]}
    assert "quads" in held and "chest" in held
    assert {"quads", "chest"}.isdisjoint(trained)
    assert all(kind in ("rest", "reduce") for kind in held.values())


def test_steady_routine_within_band_has_no_priority(catalog):
    weeks = [e for week in range(5) for e in balanced_week(week * 7, sets=6)]
    guidance = recommendation_payload(run(catalog, weeks, context(goal="general_fitness")))["guidance"]
    assert all(i["kind"] != "priority" for i in guidance["muscles"])
    assert guidance["verdict"] in ("train", "balanced", "rest")


@pytest.mark.parametrize("goal", GOALS)
@pytest.mark.parametrize("experience", ("beginner", "intermediate", "advanced"))
def test_every_profile_gets_a_valid_guidance(catalog, goal, experience):
    weeks = [e for week in range(3) for e in balanced_week(week * 7, sets=4)]
    guidance = recommendation_payload(run(catalog, weeks, context(goal=goal, experience=experience)))["guidance"]
    assert guidance["verdict"] in ("focus", "train", "rest", "balanced")
    for item in guidance["muscles"]:
        assert item["kind"] in ("priority", "train")
        assert item["params"]["sets"] >= P.MIN_SESSION_SETS
    for item in guidance["warnings"]:
        assert item["kind"] in ("rest", "reduce", "enough")
        assert item["params"]["sets"] == 0


# --- payload hygiene and i18n ----------------------------------------------


def _all_guidance_payloads(catalog):
    heavy = [entry("barbell-back-squat", d, 8, 6, 9.5, 100) for d in (0.2, 1, 2, 3)]
    weeks = [e for week in range(5) for e in balanced_week(week * 7, sets=6)]
    yield recommendation_payload(run(catalog, []))["guidance"]
    yield recommendation_payload(run(catalog, heavy))["guidance"]
    yield recommendation_payload(run(catalog, weeks))["guidance"]
    yield recommendation_payload(run(catalog, weeks, context(goal="maintenance")))["guidance"]
    for verdict in ("focus", "train", "rest", "balanced"):
        yield {"title": f"recommendations.training.guidance.verdict.{verdict}.title",
               "message": f"recommendations.training.guidance.verdict.{verdict}.message",
               "muscles": [], "warnings": []}
    yield {"title": "recommendations.training.guidance.verdict.rest.title",
           "message": "recommendations.training.guidance.verdict.rest.messageFatigue",
           "muscles": [], "warnings": []}


def test_guidance_exposes_no_internal_numbers(catalog):
    for guidance in _all_guidance_payloads(catalog):
        for item in guidance["muscles"] + guidance["warnings"]:
            assert set(item) == {"muscle", "kind", "label", "reasons", "action", "params"}
            assert set(item["params"]) == {"sets"}
            assert isinstance(item["params"]["sets"], int)
            # Only "train" items carry an action; warnings say it in the label.
            assert (item["action"] is not None) == (item["kind"] in ("priority", "train"))


def _lookup(tree, key):
    for part in key.split("."):
        if not isinstance(tree, dict) or part not in tree:
            return None
        tree = tree[part]
    return tree


@pytest.mark.parametrize("lang", LANGUAGES)
def test_every_guidance_key_is_translated(catalog, lang):
    training = json.loads((TRANSLATIONS / lang / "training.json").read_text(encoding="utf-8"))
    keys = {"recommendations.training.guidance.heading", "recommendations.training.guidance.holdBack",
            "recommendations.training.guidance.noExercises"}
    for guidance in _all_guidance_payloads(catalog):
        keys |= {guidance["title"], guidance["message"]}
        for item in guidance["muscles"] + guidance["warnings"]:
            keys |= {item["label"], *item["reasons"]}
            if item["action"]:
                keys.add(item["action"])
    for kind in ("priority", "train", "reduce", "enough", "rest"):
        keys.add(f"recommendations.training.guidance.kind.{kind}")
    for kind in ("priority", "train"):
        keys.add(f"recommendations.training.guidance.action.{kind}")
    missing = sorted(k for k in keys if not isinstance(_lookup(training, k), str))
    assert not missing


@pytest.mark.parametrize("lang", LANGUAGES)
def test_every_reason_key_is_translated_for_page_and_dashboard(lang):
    reasons = {
        "accumulatedFatigue", "lowReadiness", "highVolume", "moderateReadiness", "undertrained",
        "belowTarget", "withinTarget", "weakPoint", "focus", "frequency", "recovered", "ready",
    }
    for path in ("training.json", "dashboard/recommendations.json"):
        data = json.loads((TRANSLATIONS / lang / path).read_text(encoding="utf-8"))
        table = data["recommendations"]["training"]["reasons"]
        assert reasons <= set(table), (path, sorted(reasons - set(table)))
