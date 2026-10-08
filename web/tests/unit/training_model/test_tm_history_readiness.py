"""Exposure, local fatigue, readiness, sleep modifier and hysteresis."""

from datetime import timedelta

import pytest

from backend.app.services.training.model import parameters as P
from backend.app.services.training.model.history import (
    build_doses,
    muscle_exposure,
    muscle_fatigue,
    trend,
)
from backend.app.services.training.model.readiness import (
    hysteresis_index,
    readiness_from_fatigue,
    readiness_level,
    sleep_modifier,
)

from tm_helpers import NOW, entry, nights


def chest_doses(catalog, sessions):
    """sessions: [(days_ago, sets, rpe)] of bench press."""
    return build_doses(
        [entry("bench-press", d, n, rpe=r, session=i) for i, (d, n, r) in enumerate(sessions)],
        catalog,
    )


# --- exposure ----------------------------------------------------------------


def test_one_session_reads_as_its_sets_per_week(catalog):
    doses = chest_doses(catalog, [(0, 10, 10)])
    e7 = muscle_exposure(doses, NOW, P.EXPOSURE_RECENT_TAU_DAYS)
    assert e7["chest"] == pytest.approx(10.0)


def test_steady_training_averages_to_weekly_volume(catalog):
    """E7 ripples with the training rhythm; its average over a cycle equals
    the true weekly volume (5 sets every 3 days = 11.7 sets / week)."""
    doses = chest_doses(catalog, [(d, 5, 10) for d in range(3, 120, 3)])
    values = [
        muscle_exposure(doses, NOW - timedelta(hours=h), P.EXPOSURE_RECENT_TAU_DAYS)["chest"]
        for h in range(0, 72)
    ]
    assert sum(values) / len(values) == pytest.approx(5 * 7 / 3, rel=0.03)


def test_exposure_fades_without_cliffs(catalog):
    doses = chest_doses(catalog, [(d, 8, 8) for d in (14, 17, 21, 24, 28)])
    previous = None
    for hour in range(0, 24 * 40, 6):
        value = muscle_exposure(doses, NOW + timedelta(hours=hour), P.EXPOSURE_RECENT_TAU_DAYS)["chest"]
        if previous is not None:
            assert value <= previous
            assert previous - value < 0.1 * previous + 0.05
        previous = value


def test_older_sessions_weigh_less_than_newer(catalog):
    new = muscle_exposure(chest_doses(catalog, [(1, 5, 8)]), NOW, P.EXPOSURE_RECENT_TAU_DAYS)["chest"]
    old = muscle_exposure(chest_doses(catalog, [(10, 5, 8)]), NOW, P.EXPOSURE_RECENT_TAU_DAYS)["chest"]
    assert old < new


def test_future_sessions_are_ignored(catalog):
    doses = chest_doses(catalog, [(-1, 5, 8)])
    assert muscle_exposure(doses, NOW, P.EXPOSURE_RECENT_TAU_DAYS) == {}
    assert muscle_fatigue(doses, NOW) == {}


def test_indirect_muscles_accumulate_exposure(catalog):
    e7 = muscle_exposure(chest_doses(catalog, [(1, 10, 8)]), NOW, P.EXPOSURE_RECENT_TAU_DAYS)
    assert e7["triceps"] > 0 and e7["shoulders"] > 0


@pytest.mark.parametrize(
    "recent, longer, expected",
    [(10, 10, "stable"), (14, 10, "up"), (6, 10, "down"), (0.2, 0, "stable"), (3, 0, "up")],
)
def test_trend_has_a_dead_band(recent, longer, expected):
    assert trend(recent, longer) == expected


# --- fatigue and readiness ------------------------------------------------


def test_readiness_is_bounded_and_decreasing_in_fatigue():
    values = [readiness_from_fatigue(f / 4) for f in range(0, 200)]
    assert all(0.0 < v <= 1.0 for v in values)
    assert all(a > b for a, b in zip(values, values[1:]))


def test_fatigue_decays_and_old_fatigue_disappears(catalog):
    doses = chest_doses(catalog, [(0, 10, 10)])
    values = [muscle_fatigue(doses, NOW + timedelta(hours=h))["chest"] for h in (0, 24, 48, 72, 24 * 30)]
    assert all(a > b for a, b in zip(values, values[1:]))
    assert readiness_from_fatigue(values[-1]) > 0.999


def test_more_sets_or_closer_to_failure_mean_slower_readiness(catalog):
    later = NOW + timedelta(hours=48)

    def readiness(sets, rpe):
        return readiness_from_fatigue(muscle_fatigue(chest_doses(catalog, [(0, sets, rpe)]), later)["chest"])

    assert readiness(6, 8) > readiness(10, 8) > readiness(12, 8)
    assert readiness(10, 7) > readiness(10, 8) > readiness(10, 10)


# --- sleep -----------------------------------------------------------------


def test_missing_sleep_data_is_neutral():
    assert sleep_modifier([], NOW.date()) == 1.0


def test_sleep_modifier_is_gradual_and_bounded():
    short = 300  # 5 h
    one = sleep_modifier(nights({0: short}), NOW.date())
    three = sleep_modifier(nights({i: short for i in range(3)}), NOW.date())
    seven = sleep_modifier(nights({i: short for i in range(7)}), NOW.date())
    terrible = sleep_modifier(nights({i: 60 for i in range(14)}), NOW.date())
    assert 1.0 > one > three > seven >= terrible >= 1.0 - P.SLEEP_MAX_READINESS_PENALTY
    assert one > 0.94  # one bad night is a small nudge, not a reset


def test_enough_sleep_has_no_effect():
    assert sleep_modifier(nights({i: 480 for i in range(7)}), NOW.date()) == 1.0


def test_old_bad_nights_matter_less():
    recent = sleep_modifier(nights({0: 300}), NOW.date())
    old = sleep_modifier(nights({4: 300}), NOW.date())
    assert recent < old < 1.0


# --- levels and hysteresis -------------------------------------------------


@pytest.mark.parametrize(
    "score, level",
    [(0.2, "low"), (0.5, "moderate"), (0.7, "ready"), (0.9, "recovered"), (1.0, "recovered")],
)
def test_readiness_levels(score, level):
    assert readiness_level(score) == level


def test_hysteresis_keeps_level_near_the_bound():
    bound = P.READINESS_LEVELS[2][1]  # "ready"
    below = readiness_level(bound - 0.01)
    assert below == "moderate"
    # Coming from "moderate", a value just above the bound keeps "moderate".
    assert readiness_level(bound + 0.01, previous=1) == "moderate"
    assert readiness_level(bound + P.READINESS_HYSTERESIS + 0.01, previous=1) == "ready"
    # Coming from "ready", a value just below keeps "ready".
    assert readiness_level(bound - 0.01, previous=2) == "ready"
    assert readiness_level(bound - P.READINESS_HYSTERESIS - 0.01, previous=2) == "moderate"


def test_hysteresis_can_jump_several_levels():
    assert hysteresis_index(0.99, (0.0, 0.45, 0.65, 0.85), 0, 0.05) == 3
    assert hysteresis_index(0.01, (0.0, 0.45, 0.65, 0.85), 3, 0.05) == 0
