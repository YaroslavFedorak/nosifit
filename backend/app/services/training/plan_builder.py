"""Deterministic weekly plan builder (no AI, no external services).

The split templates (``training/data/templates/splits``) only say which muscle
groups a day covers. Everything else comes from the training model:

    training days -> split -> template days placed on the calendar
        -> for each day, in order:
             Stage 1 allocation (``allocate_sets``) of what is still missing
             from the weekly band, given the sets already planned this week
             -> Stage 2 exercise selection (``select_exercises``)
             -> the sets delivered join the virtual weekly exposure

The planned week plays the part of the training history, so later days see
what earlier days already covered and exercises are not repeated without
reason. When the week cannot be covered (equipment, a day cap) the plan stays
shorter and says so; it is never padded.
"""

import itertools
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Collection, Dict, List, Mapping, Optional, Sequence, Tuple

from backend.app.utils.validation import ValidationError

from . import plan_days
from .model import parameters as P
from .model.context import TrainingContext
from .model.priority import MusclePlan, allocate_sets, focus_modifier
from .model.records import ExerciseInfo
from .model.selection import ExercisePrescription, is_suitable, pattern_family, select_exercises
from .model.status import weekly_targets
from .model.stimulus import contribution_weights, set_stimulus

MAX_TRAINING_DAYS = 6  # at least one rest day a week
MAX_WEEKLY_REPEATS = 2  # one exercise at most twice a week
DAY_EXERCISE_LIMIT = {"beginner": 5, "intermediate": 6, "advanced": 7}
MIN_DAY_EXERCISES = 3  # floor of the per-day cap for the experience level
MIN_WORKOUT_EXERCISES = 2  # a day with fewer exercises is not a workout
# Template day (file, key) per training day for each number of days a week.
SEQUENCES: Dict[int, Tuple[Tuple[str, str], ...]] = {
    1: (("full_body", "day1"),),
    2: (("full_body", "day1"), ("full_body", "day2")),
    3: (("full_body", "day1"), ("full_body", "day2"), ("full_body", "day3")),
    4: (("upper_lower", "upper"), ("upper_lower", "lower")) * 2,
    5: (("ppl", "push"), ("ppl", "pull"), ("ppl", "legs"), ("upper_lower", "upper"), ("upper_lower", "lower")),
    6: (("ppl", "push"), ("ppl", "pull"), ("ppl", "legs")) * 2,
}
SPLIT_NAMES = {1: "full_body", 2: "full_body", 3: "full_body", 4: "upper_lower", 5: "ppl_upper_lower", 6: "ppl"}
DEFAULT_SCHEDULES = {
    1: ("wed",),
    2: ("mon", "thu"),
    3: ("mon", "wed", "fri"),
    4: ("mon", "tue", "thu", "fri"),
    5: ("mon", "tue", "wed", "fri", "sat"),
    6: ("mon", "tue", "wed", "thu", "fri", "sat"),
}
_DATA = Path(__file__).resolve().parents[2] / "training" / "data"
_TEMPLATES = _DATA / "templates" / "splits"
_ANCHOR = datetime(2001, 1, 1)  # a Monday; only differences between days matter
_RESTED = SimpleNamespace(readiness_score=1.0)  # every session is planned for a rested muscle


@dataclass
class PlannedDay:
    key: str
    label: str
    location: str
    equipment: Optional[List[str]]
    muscles: Tuple[str, ...]
    exercises: List[ExercisePrescription] = field(default_factory=list)


@dataclass
class GeneratedWeek:
    split: str
    days: Dict[str, PlannedDay]
    rest_days: List[str]
    coverage: Dict[str, Dict[str, float]]
    notes: List[Dict[str, Any]]

    def to_payload(self) -> Dict[str, Any]:
        """Plan days in the shape the plan API stores, plus the explanation."""
        return {
            "split": self.split,
            "rest_days": self.rest_days,
            "days": {
                key: {
                    "location": day.location,
                    "equipment": day.equipment,
                    "exercises": [
                        {
                            "exercise": {"id": item.exercise.id},
                            "sets": item.sets,
                            "reps": item.reps,
                            "duration_sec": item.duration_sec,
                            "load": 0,
                        }
                        for item in day.exercises
                    ],
                }
                for key, day in self.days.items()
            },
            "explanation": {
                key: {
                    "label": day.label,
                    "muscles": list(day.muscles),
                    "exercises": [
                        {
                            "id": item.exercise.id,
                            "muscles": list(item.target_muscles),
                            "target_rir": list(item.target_rir),
                        }
                        for item in day.exercises
                    ],
                }
                for key, day in self.days.items()
            },
            "coverage": self.coverage,
            "notes": self.notes,
        }


def load_template(split: str) -> Mapping[str, Any]:
    with open(_TEMPLATES / f"{split}.json", "r", encoding="utf-8") as handle:
        return json.load(handle)


def _library_file() -> Mapping[str, Any]:
    with open(_DATA / "plan_library.json", "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_library() -> frozenset:
    """Slugs of the conventional exercises the builder may recommend."""
    return frozenset(slug for slugs in _library_file()["categories"].values() for slug in slugs)


def load_variant_groups() -> Dict[str, str]:
    """slug -> group of exercises that are variants of one movement."""
    return {
        slug: group
        for group, slugs in _library_file().get("same_exercise_groups", {}).items()
        for slug in slugs
    }


def _first_variant_clash(
    picked: Sequence[ExercisePrescription], groups: Mapping[str, str]
) -> Optional[ExercisePrescription]:
    """The later of two picks that are variants of the same movement."""
    seen = set()
    for item in picked:
        group = groups.get(item.exercise.slug)
        if group is None:
            continue
        if group in seen:
            return item
        seen.add(group)
    return None


def default_training_days(workouts_per_week: int) -> Tuple[str, ...]:
    return DEFAULT_SCHEDULES[max(1, min(int(workouts_per_week or 1), MAX_TRAINING_DAYS))]


def clean_training_days(value: Any, context: TrainingContext) -> List[str]:
    """Selected training days in week order; the rest of the week is rest."""
    if value in (None, []):
        return list(default_training_days(context.workouts_per_week))
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValidationError("training_days must be a list of weekdays")
    days = {item.strip().lower() for item in value}
    if not days <= set(plan_days.WEEKDAYS):
        raise ValidationError("unknown day")
    if len(days) > MAX_TRAINING_DAYS:
        raise ValidationError("at least one rest day a week is required")
    return [day for day in plan_days.WEEKDAYS if day in days]


def _template_muscles(
    template: Mapping[str, Any],
    by_slug: Mapping[str, ExerciseInfo],
) -> Tuple[str, ...]:
    """Major muscles a template day trains directly (at least one full set)."""
    totals: Dict[str, float] = defaultdict(float)
    for item in template.get("exercises", []):
        exercise = by_slug.get(item.get("id"))
        if exercise is None:
            continue
        for muscle, weight in contribution_weights(exercise).items():
            totals[muscle] += weight
    return tuple(m for m in P.MAJOR_MUSCLES if totals.get(m, 0.0) >= 1.0)


def _place_on_calendar(
    days: Sequence[str],
    sequence: Sequence[Tuple[str, Tuple[str, ...]]],
) -> Tuple[int, ...]:
    """Order template days so back-to-back calendar days share the fewest muscles."""
    index = [plan_days.WEEKDAYS.index(day) for day in days]
    adjacent = {
        (a, b)
        for a, b in zip(range(len(days)), range(1, len(days)))
        if index[b] - index[a] == 1
    }
    if len(days) > 2 and index[0] + 7 - index[-1] == 1:
        adjacent.add((len(days) - 1, 0))

    def cost(order: Tuple[int, ...]) -> int:
        return sum(len(set(sequence[order[a]][1]) & set(sequence[order[b]][1])) for a, b in adjacent)

    return min(itertools.permutations(range(len(days))), key=lambda order: (cost(order), order))


def _order_exercises(items: Sequence[ExercisePrescription]) -> List[ExercisePrescription]:
    """Big lifts first, isolation and core work last."""

    def rank(item: ExercisePrescription):
        family = pattern_family(item.exercise)
        late = 2 if family == "core" else 1 if family == "isolation" else 0
        return (late, -len(contribution_weights(item.exercise)), item.exercise.slug)

    return sorted(items, key=rank)


def build_week(
    context: TrainingContext,
    catalog: Mapping[str, ExerciseInfo],
    *,
    training_days: Optional[Sequence[str]] = None,
    day_settings: Optional[Mapping[str, Mapping[str, Any]]] = None,
    owned_equipment: Sequence[str] = (),
    templates=load_template,
    library: Optional[Collection[str]] = None,
) -> GeneratedWeek:
    days = clean_training_days(list(training_days) if training_days else None, context)
    settings = day_settings or {}
    by_slug = {exercise.slug: exercise for exercise in catalog.values()}
    # Without a list of owned equipment, a home or outdoor day gets what the
    # context allows (None there means a gym user: nothing owned is known).
    if not owned_equipment and context.available_equipment is not None:
        owned_equipment = sorted(context.available_equipment - {plan_days.BODYWEIGHT})
    allowed = load_library() if library is None else frozenset(library)
    variants = load_variant_groups() if library is None else {}
    default_location = "gym" if context.available_equipment is None else "home"

    sequence = []
    for split_file, template_key in SEQUENCES[len(days)]:
        template = templates(split_file)["days"][template_key]
        # Full-body days differ only by number; they share one label.
        label = split_file if split_file == "full_body" else template_key
        sequence.append((label, _template_muscles(template, by_slug)))
    order = _place_on_calendar(days, sequence)

    lower, upper = weekly_targets(context)
    sessions = Counter(m for pos in order for m in sequence[pos][1])
    exposure: Dict[str, float] = defaultdict(float)
    uses: Counter = Counter()
    last_done: Dict[str, datetime] = {}
    limit = DAY_EXERCISE_LIMIT[context.experience]
    if len(days) >= 5:
        limit -= 1
    limit = max(limit, MIN_DAY_EXERCISES)

    planned: Dict[str, PlannedDay] = {}
    notes: List[Dict[str, Any]] = []

    for position, key in enumerate(days):
        label, muscles = sequence[order[position]]
        meta = settings.get(key) or {}
        location = plan_days.clean_location(meta.get("location")) or default_location
        equipment = plan_days.clean_equipment(meta.get("equipment"))
        available = plan_days.available_equipment(location, equipment, owned_equipment)
        day_context = replace(context, available_equipment=available)
        moment = _ANCHOR + timedelta(days=plan_days.WEEKDAYS.index(key))

        plans = []
        for muscle in P.MAJOR_MUSCLES:
            if muscle not in muscles:
                continue
            is_weak = muscle in context.weak_muscles
            emphasised = is_weak or focus_modifier(context.focus.get(muscle), is_weak) > 1.0
            band_low, band_high = (upper, upper) if emphasised else (lower, upper)
            sets = allocate_sets(exposure[muscle], band_low, band_high, sessions[muscle], 1.0)
            plans.append(
                MusclePlan(
                    muscle=muscle, priority=1.0, need=1.0, availability=1.0,
                    weak_modifier=1.0, focus_modifier=1.0, opportunity=1.0,
                    allocated_sets=sets, targeted=sets > 0, action="train", reasons=(),
                )
            )

        # A muscle that already reached the top of its weekly band takes no
        # more work, not even as a side effect of another exercise.
        full = {m for m in P.MAJOR_MUSCLES if exposure[m] >= upper}
        candidates = [
            exercise
            for exercise in catalog.values()
            if exercise.slug in allowed
            and uses[exercise.id] < MAX_WEEKLY_REPEATS
            and is_suitable(exercise, day_context)
            and not any(
                weight >= P.INDIRECT_SET_CAP and muscle in full
                for muscle, weight in contribution_weights(exercise).items()
            )
        ]
        while True:
            picked = select_exercises(
                plans,
                {m: _RESTED for m in P.MAJOR_MUSCLES},
                candidates,
                day_context,
                last_done,
                moment,
                limit=limit,
            )
            clash = _first_variant_clash(picked, variants)
            if clash is None:
                break
            candidates = [c for c in candidates if c.id != clash.exercise.id]

        for item in picked:
            per_set = set_stimulus(sum(item.target_rir) / 2.0)
            for muscle, weight in contribution_weights(item.exercise).items():
                exposure[muscle] += item.sets * per_set * weight
            uses[item.exercise.id] += 1
            last_done[item.exercise.id] = moment

        planned[key] = PlannedDay(
            key=key,
            label=label,
            location=location,
            equipment=None if available is None else sorted(available - {plan_days.BODYWEIGHT}),
            muscles=muscles,
            exercises=_order_exercises(picked),
        )

    # A day the weekly volume does not need (nothing, or a single exercise)
    # stays a rest day instead of an empty or one-exercise "workout".
    for key in [k for k, day in planned.items() if len(day.exercises) < MIN_WORKOUT_EXERCISES]:
        del planned[key]
        notes.append({"code": "no_exercises", "day": key})

    # The week as it ended up, not as it was planned: dropped days add nothing.
    exposure = defaultdict(float)
    for day in planned.values():
        for item in day.exercises:
            per_set = set_stimulus(sum(item.target_rir) / 2.0)
            for muscle, weight in contribution_weights(item.exercise).items():
                exposure[muscle] += item.sets * per_set * weight

    coverage = {
        muscle: {"planned": round(exposure[muscle], 1), "lower": lower, "upper": upper}
        for muscle in P.MAJOR_MUSCLES
        if exposure[muscle] > 0
    }
    short = [m for m, row in coverage.items() if row["planned"] < lower]
    if short:
        notes.append({"code": "volume_short", "muscles": short})
    high = [m for m, row in coverage.items() if row["planned"] > upper]
    if high:
        notes.append({"code": "volume_high", "muscles": high})
    skipped = [m for m in P.MAJOR_MUSCLES if not exposure[m]]
    if skipped:
        notes.append({"code": "split_skips", "muscles": skipped})
    kept = [day for day in days if day in planned]
    for first, second in zip(kept, kept[1:] + kept[:1]):
        gap = (plan_days.WEEKDAYS.index(second) - plan_days.WEEKDAYS.index(first)) % 7
        shared = sorted(set(planned[first].muscles) & set(planned[second].muscles))
        if gap == 1 and shared and first != second:
            notes.append({"code": "back_to_back", "days": [first, second], "muscles": shared})

    return GeneratedWeek(
        split=SPLIT_NAMES[len(days)],
        days=planned,
        rest_days=[day for day in plan_days.WEEKDAYS if day not in planned],
        coverage=coverage,
        notes=notes,
    )
