"""Stage 2: which exercises best cover the muscle needs chosen in Stage 1.

    score = target contribution + goal fit + pattern diversity
            - fatigue conflict - recent repetition

Selection is greedy and marginal: after an exercise is picked, the sets it
delivers are subtracted from the remaining needs, so the next pick covers
what is still missing. Ties break by slug, so the result is deterministic.
Difficulty and risk only filter exercises; they never scale stimulus.
"""

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from backend.app.training.exercises.prescription import default_entry

from . import parameters as P
from .context import TrainingContext
from .numeric import clamp, round_half_up
from .priority import MusclePlan, availability
from .records import ExerciseInfo
from .status import MuscleStatus
from .stimulus import contribution_weights, is_training_exercise, set_stimulus

LOADED_TYPES = ("external", "machine", "cable")


@dataclass(frozen=True)
class ExercisePrescription:
    exercise: ExerciseInfo
    sets: int
    reps: Optional[str]
    duration_sec: Optional[int]
    per_side: bool
    target_rir: Tuple[int, int]
    target_muscles: Tuple[str, ...]
    score: float
    reasons: Tuple[str, ...]


def pattern_family(exercise: ExerciseInfo) -> str:
    return P.PATTERN_FAMILIES.get(exercise.movement_pattern, "other")


def is_suitable(exercise: ExerciseInfo, context: TrainingContext) -> bool:
    if not is_training_exercise(exercise):
        return False
    if exercise.difficulty > P.MAX_DIFFICULTY[context.experience]:
        return False
    if exercise.risk_level > P.MAX_RISK[context.experience]:
        return False
    if context.available_equipment is not None:
        required = set(exercise.equipment) - {"bodyweight"}
        if not required <= context.available_equipment:
            return False
    return True


def target_rir(exercise: ExerciseInfo, context: TrainingContext) -> Tuple[int, int]:
    kind = "isolation" if pattern_family(exercise) == "isolation" else "compound"
    low, high = P.TARGET_RIR[context.goal][kind]
    if context.experience == "beginner":
        low, high = low + P.BEGINNER_EXTRA_RIR, high + P.BEGINNER_EXTRA_RIR
    return int(low), int(high)


def _reps(exercise: ExerciseInfo, context: TrainingContext, entry) -> Optional[str]:
    if entry["reps"] is None:
        return None
    if (
        context.goal == "strength"
        and exercise.load_type in LOADED_TYPES
        and pattern_family(exercise) not in ("isolation", "conditioning")
    ):
        low, high = P.STRENGTH_REP_RANGE
        return f"{low}-{high}"
    return entry["reps"]


def select_exercises(
    plans: Sequence[MusclePlan],
    statuses: Mapping[str, MuscleStatus],
    catalog: Sequence[ExerciseInfo],
    context: TrainingContext,
    last_done: Mapping[str, datetime],
    now: datetime,
) -> List[ExercisePrescription]:
    remaining: Dict[str, float] = {
        p.muscle: float(p.allocated_sets) for p in plans if p.targeted and p.allocated_sets > 0
    }
    reasons_by_muscle = {p.muscle: p.reasons for p in plans}
    avail = {m: availability(s.readiness_score) for m, s in statuses.items()}
    weights = P.SELECTION_WEIGHTS
    fit_table = P.GOAL_PATTERN_FIT[context.goal]
    load_fit_table = P.LOAD_TYPE_FIT[context.goal]

    candidates = sorted(
        (x for x in catalog if is_suitable(x, context)),
        key=lambda x: x.slug,
    )
    chosen: List[ExercisePrescription] = []
    chosen_ids = set()
    chosen_families = set()

    while len(chosen) < P.MAX_RECOMMENDED_EXERCISES:
        total = sum(remaining.values())
        if total <= 0:
            break

        best = None
        for exercise in candidates:
            if exercise.id in chosen_ids:
                continue
            contribution = contribution_weights(exercise)
            main_muscle, main_value = _main_target(contribution, remaining)
            if main_muscle is None or contribution[main_muscle] < P.INDIRECT_SET_CAP:
                continue

            target = sum(w * remaining.get(m, 0.0) for m, w in contribution.items()) / total
            weight_sum = sum(contribution.values()) or 1.0
            conflict = sum(w * (1.0 - avail.get(m, 1.0)) for m, w in contribution.items()) / weight_sum
            family = pattern_family(exercise)
            done = last_done.get(exercise.id)
            recent = (
                math.exp(-((now - done).total_seconds() / 86400.0) / P.RECENT_REPETITION_TAU_DAYS)
                if done is not None
                else 0.0
            )
            score = (
                weights["target"] * target
                + weights["goal_fit"]
                * fit_table.get(family, P.GOAL_FIT_DEFAULT)
                * load_fit_table.get(exercise.load_type or "none", P.GOAL_FIT_DEFAULT)
                + weights["diversity"] * (0.0 if family in chosen_families else 1.0)
                - weights["fatigue_conflict"] * conflict
                - weights["recent_repetition"] * recent
            )
            # Among equal scores prefer the technically simpler exercise.
            key = (-round(score, 9), exercise.difficulty, exercise.slug)
            if best is None or key < best[0]:
                best = (key, exercise, score, contribution, main_muscle)

        if best is None:
            break

        _, exercise, score, contribution, main_muscle = best
        rir_low, rir_high = target_rir(exercise, context)
        per_set = set_stimulus((rir_low + rir_high) / 2.0)
        needed_sets = remaining[main_muscle] / (contribution[main_muscle] * per_set)
        sets = int(clamp(round_half_up(needed_sets), P.MIN_SESSION_SETS, P.MAX_SETS_PER_EXERCISE))

        covered = []
        for muscle in list(remaining):
            delivered = sets * per_set * contribution.get(muscle, 0.0)
            if delivered > 0:
                covered.append(muscle)
            remaining[muscle] = max(remaining[muscle] - delivered, 0.0)

        entry = default_entry(exercise)
        chosen.append(
            ExercisePrescription(
                exercise=exercise,
                sets=sets,
                reps=_reps(exercise, context, entry),
                duration_sec=entry["duration_sec"],
                per_side=bool(entry["per_side"]),
                target_rir=(rir_low, rir_high),
                target_muscles=tuple(sorted(covered, key=lambda m: -contribution[m])),
                score=score,
                reasons=reasons_by_muscle.get(main_muscle, ()),
            )
        )
        chosen_ids.add(exercise.id)
        chosen_families.add(pattern_family(exercise))

    return chosen


def _main_target(contribution: Mapping[str, float], remaining: Mapping[str, float]):
    best = (None, 0.0)
    for muscle in sorted(contribution):
        value = contribution[muscle] * remaining.get(muscle, 0.0)
        if value > best[1]:
            best = (muscle, value)
    return best
