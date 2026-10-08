"""Heatmap intensity_percent: presentation of the session stress proxy."""

from datetime import date, timedelta

import pytest

from backend.app.services.training.model import parameters as P
from backend.app.services.training.model.session_stress import (
    day_levels,
    heatmap_typical_stress,
    intensity_percent,
)

TODAY = date(2026, 10, 8)


@pytest.mark.parametrize(
    "ratio, expected",
    [(0.0, 0), (0.5, 33), (0.75, 50), (1.0, 67), (1.25, 83), (1.5, 100), (3.0, 100)],
)
def test_ratio_to_percent_anchors(ratio, expected):
    assert intensity_percent(ratio * 20.0, 20.0) == expected


def test_percent_is_monotone_bounded_and_without_jumps():
    values = [intensity_percent(v / 10, 20.0) for v in range(0, 600)]
    assert all(0 <= v <= 100 for v in values)
    assert all(a <= b for a, b in zip(values, values[1:]))
    assert max(b - a for a, b in zip(values, values[1:])) <= 1


def test_any_training_day_is_visible():
    assert intensity_percent(0.01, 20.0) == 1
    assert intensity_percent(0.0, 20.0) == 0


def test_new_user_baseline_is_the_prior():
    levels = day_levels({TODAY: P.HEATMAP_PRIOR_TYPICAL_STRESS}, [TODAY])
    assert levels[TODAY]["intensity_percent"] == 67


def test_baseline_moves_smoothly_from_prior_to_own_median():
    """Regression: a hard floor overrode the history of users whose familiar
    sessions sit below it, so their typical session read 54% instead of ~67%."""
    previous = None
    for count in range(0, 30):
        history = {TODAY - timedelta(days=d): 10.0 for d in range(1, count + 1)}
        value = heatmap_typical_stress(history, TODAY)
        if previous is not None:
            assert value <= previous and previous - value < 1.5
        previous = value
    assert previous == pytest.approx(10.0, abs=1.0)


def test_recovery_baseline_keeps_its_own_floor():
    """The recovery notes' typical session is not affected by the heatmap floor."""
    levels = day_levels({TODAY: 5.0}, [TODAY])
    assert levels[TODAY]["typical"] == P.STRESS_MIN_TYPICAL_SETS


def test_typical_session_of_an_established_user_reads_about_two_thirds():
    for typical in (8.0, 20.0):
        history = {TODAY - timedelta(days=d): typical for d in range(2, 40, 2)}
        history[TODAY] = typical
        assert 60 <= day_levels(history, [TODAY])[TODAY]["intensity_percent"] <= 72


def test_past_days_do_not_change_when_today_is_added():
    history = {TODAY - timedelta(days=d): 18.0 for d in range(1, 30, 3)}
    days = sorted(history)
    before = day_levels(history, days)
    after = day_levels({**history, TODAY: 60.0}, days)
    assert before == after
