"""Stage 1: which muscles to train next, and how many sets this session.

    priority = need x availability x weak_point_modifier x focus_modifier x opportunity

* need          - how far recent exposure (E7) is below the middle of the
                  goal/experience band; 0 once the band middle is reached.
* availability  - smoothstep of readiness; a fatigued muscle gets 0, so no
                  modifier can make it a priority.
* weak / focus  - small priority modifiers; they never touch stimulus,
                  fatigue or readiness.
* opportunity   - muscles trained very recently yield to the others.

Session allocation splits the weekly band over the expected sessions and caps
it per session, so a weekly target never turns into one huge workout.
"""

from dataclasses import dataclass
from typing import List, Mapping, Optional, Tuple

from . import parameters as P
from .context import TrainingContext
from .numeric import clamp, round_half_up, smoothstep
from .status import MuscleStatus, weekly_targets


@dataclass(frozen=True)
class MusclePlan:
    muscle: str
    priority: float
    need: float
    availability: float
    weak_modifier: float
    focus_modifier: float
    opportunity: float
    allocated_sets: int  # effective sets this muscle could take this session
    targeted: bool  # chosen for Stage 2 (top priorities)
    action: str  # prioritize | train | maintain | reduce_volume | rest
    reasons: Tuple[str, ...]


def availability(readiness_score: float) -> float:
    return smoothstep(P.AVAILABILITY_LOW, P.AVAILABILITY_HIGH, readiness_score)


def need(exposure_recent: float, lower: float, upper: float) -> float:
    middle = (lower + upper) / 2.0
    return clamp((middle - exposure_recent) / middle, 0.0, 1.0)


def weak_modifier(is_weak: bool) -> float:
    return 1.0 + P.WEAK_POINT_BONUS if is_weak else 1.0


def focus_modifier(focus: Optional[float], is_weak: bool) -> float:
    if focus is None:
        return 1.0
    shift = clamp((float(focus) - P.FOCUS_NEUTRAL) / P.FOCUS_SPAN, -1.0, 1.0)
    value = 1.0 + P.FOCUS_MAX_ADJUSTMENT * shift
    # A real weak point outweighs a low onboarding focus.
    return max(value, 1.0) if is_weak else value


def exposures_per_week(context: TrainingContext) -> int:
    return int(clamp(context.workouts_per_week, 1, P.MAX_EXPOSURES_PER_WEEK))


def target_interval_days(context: TrainingContext) -> float:
    return 7.0 / max(P.MIN_EXPOSURES_PER_WEEK, exposures_per_week(context))


def opportunity(days_since_trained: Optional[float], interval_days: float) -> float:
    days = interval_days if days_since_trained is None else days_since_trained
    return P.OPPORTUNITY_FLOOR + (1.0 - P.OPPORTUNITY_FLOOR) * smoothstep(0.0, interval_days, days)


def allocate_sets(exposure_recent: float, lower: float, upper: float, sessions: int, avail: float) -> int:
    middle = (lower + upper) / 2.0
    remaining = max(middle - exposure_recent, 0.0)
    # Small weekly bands are not split into sub-minimum sessions: the muscle is
    # trained less often instead.
    per_session = max(middle / max(sessions, 1), P.MIN_SESSION_SETS)
    base = min(per_session, remaining, P.SESSION_SET_CAP_PER_MUSCLE)
    sets = round_half_up(base * avail)
    return sets if sets >= P.MIN_SESSION_SETS else 0


def plan_muscles(statuses: Mapping[str, MuscleStatus], context: TrainingContext) -> List[MusclePlan]:
    lower, upper = weekly_targets(context)
    sessions = exposures_per_week(context)
    interval = target_interval_days(context)

    scored = []
    for muscle in P.MAJOR_MUSCLES:
        status = statuses.get(muscle)
        if status is None:
            continue
        is_weak = muscle in context.weak_muscles
        focus = context.focus.get(muscle)
        avail = availability(status.readiness_score)
        components = (
            need(status.exposure_recent, lower, upper),
            avail,
            weak_modifier(is_weak),
            focus_modifier(focus, is_weak),
            opportunity(status.days_since_trained, interval),
        )
        priority = 1.0
        for value in components:
            priority *= value
        sets = allocate_sets(status.exposure_recent, lower, upper, sessions, avail)
        scored.append((muscle, priority, components, sets, status, is_weak, focus))

    tie_order = {m: i for i, m in enumerate(P.STAGE1_TIE_BREAK_ORDER)}
    ranked = sorted(
        scored,
        key=lambda item: (-round(item[1], 9), tie_order.get(item[0], len(tie_order)), item[0]),
    )
    targets = {
        item[0]
        for item in ranked
        if item[1] >= P.MIN_PRIORITY and item[3] > 0
    }
    targets = set(
        [item[0] for item in ranked if item[0] in targets][: P.MAX_TARGET_MUSCLES]
    )

    plans = []
    for muscle, priority, components, sets, status, is_weak, focus in ranked:
        action = _action(status, muscle in targets, sets)
        plans.append(
            MusclePlan(
                muscle=muscle,
                priority=priority,
                need=components[0],
                availability=components[1],
                weak_modifier=components[2],
                focus_modifier=components[3],
                opportunity=components[4],
                allocated_sets=sets,
                targeted=muscle in targets,
                action=action,
                reasons=_reasons(status, is_weak, focus, action),
            )
        )
    return plans


def _action(status: MuscleStatus, targeted: bool, sets: int) -> str:
    if status.accumulated_fatigue or status.readiness_level == "low":
        return "rest"
    if status.readiness_level == "moderate" or status.high_volume:
        return "reduce_volume"
    if targeted:
        return "prioritize"
    if sets > 0:
        return "train"
    return "maintain"


def _reasons(status: MuscleStatus, is_weak: bool, focus: Optional[float], action: str) -> Tuple[str, ...]:
    base = "recommendations.training.reasons."
    reasons = []
    if action == "rest":
        reasons.append(base + ("accumulatedFatigue" if status.accumulated_fatigue else "lowReadiness"))
    elif action == "reduce_volume":
        reasons.append(base + ("highVolume" if status.high_volume else "moderateReadiness"))
    if status.underloaded:
        reasons.append(base + "undertrained")
    elif status.below_target:
        reasons.append(base + "belowTarget")
    if is_weak:
        reasons.append(base + "weakPoint")
    elif focus is not None and focus > P.FOCUS_NEUTRAL:
        reasons.append(base + "focus")
    guideline_interval = 7.0 / P.MIN_EXPOSURES_PER_WEEK
    if status.days_since_trained is None or status.days_since_trained > guideline_interval:
        reasons.append(base + "frequency")
    if action in ("prioritize", "train") and status.readiness_level == "recovered":
        reasons.append(base + "recovered")
    return tuple(reasons)
