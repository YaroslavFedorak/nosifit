"""Weekly sets widget: calendar week, aggregation of stored muscle_loads, target."""

from datetime import date

import pytest

from backend.app.services.training.model import parameters as P
from backend.app.services.training.model.priority import need
from backend.app.services.training.model.weekly_sets import (
    week_start,
    weekly_muscle_sets,
    weekly_target_sets,
)

from tm_helpers import context


@pytest.mark.parametrize(
    "day, monday",
    [
        (date(2026, 10, 5), date(2026, 10, 5)),  # Monday is its own week start
        (date(2026, 10, 7), date(2026, 10, 5)),  # Wednesday
        (date(2026, 10, 11), date(2026, 10, 5)),  # Sunday still belongs to that week
        (date(2026, 10, 12), date(2026, 10, 12)),  # next Monday starts a new week
        (date(2026, 1, 1), date(2025, 12, 29)),  # week across the new year
    ],
)
def test_week_starts_on_monday(day, monday):
    assert week_start(day) == monday


def by_muscle(result):
    return {row["muscle"]: row for row in result["muscles"]}


def test_sums_stored_sets_over_sessions():
    result = weekly_muscle_sets(
        [{"chest": 4.0, "triceps": 2.0}, {"chest": 3.5, "quads": 6.0}],
        context(),
    )
    rows = by_muscle(result)
    assert rows["chest"]["sets"] == 7.5
    assert rows["triceps"]["sets"] == 2.0
    assert rows["quads"]["sets"] == 6.0
    assert rows["lats"]["sets"] == 0.0


def test_lists_every_major_muscle_in_model_order():
    result = weekly_muscle_sets([], context())
    assert [row["muscle"] for row in result["muscles"]] == list(P.MAJOR_MUSCLES)
    assert all(row["sets"] == 0 for row in result["muscles"])


def test_ignores_minor_muscles_legacy_rows_and_bad_values():
    result = weekly_muscle_sets(
        [
            {"forearms": 3.0, "neck": 1.0},  # tracked by the model, but no weekly target
            {"42": 480.0, "bench-press": 120.0},  # pre-v2 rows held exercise ids
            ["chest", "lats"],
            None,
            {"chest": "4", "lats": True, "quads": -2.0, "glutes": float("nan")},
            {"chest": 2.0},
        ],
        context(),
    )
    rows = by_muscle(result)
    assert set(rows) == set(P.MAJOR_MUSCLES)
    assert rows["chest"]["sets"] == 2.0
    assert rows["lats"]["sets"] == rows["quads"]["sets"] == rows["glutes"]["sets"] == 0.0


@pytest.mark.parametrize("goal", ["maintenance", "general_fitness", "fat_loss", "strength", "hypertrophy"])
@pytest.mark.parametrize("experience", ["beginner", "intermediate", "advanced"])
def test_target_is_the_middle_of_the_model_band(goal, experience):
    lower, upper = P.WEEKLY_SET_TARGETS[goal][experience]
    ctx = context(goal=goal, experience=experience)
    target = weekly_target_sets(ctx)

    assert target == (lower + upper) / 2
    # The same point Stage 1 aims for: need is zero exactly at the target.
    assert need(target, lower, upper) == 0
    assert need(target - 0.5, lower, upper) > 0
    assert all(row["target_sets"] == target for row in weekly_muscle_sets([], ctx)["muscles"])


def test_focus_changes_priority_not_the_weekly_target():
    neutral = context(focus={})
    focused = context(focus={"chest": 10.0, "quads": 0.0, "abs": 10.0})
    assert weekly_muscle_sets([], neutral) == weekly_muscle_sets([], focused)
