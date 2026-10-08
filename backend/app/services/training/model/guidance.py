"""What to train today and why: the user-facing reading of Stage 1.

Nothing is computed here. Every decision reads a result the model already
has: the Stage 1 order (priority), plan action, targeting and allocated sets,
the volume zone against the LOWER/UPPER weekly band, readiness level,
accumulated fatigue and the plan's reason keys.

    kind      when
    rest      plan action "rest" (low readiness or accumulated fatigue)
    enough    volume zone "above" - no extra volume is suggested
    reduce    plan action "reduce_volume" (moderate readiness)
    priority  targeted by Stage 1 and below the weekly band
    train     targeted or allocated sets, within the band

    verdict     when
    no_history  no logged training in the model window
    focus       at least one "priority" muscle
    train       no priority, but something to train or keep up
    rest        nothing to train and no major muscle is ready
    balanced    nothing to train, some muscles ready - follow the planned
                workout (tired muscles still show as warnings)
"""

from dataclasses import dataclass
from typing import Mapping, Optional, Sequence, Tuple

from . import parameters as P
from .priority import MusclePlan
from .status import MuscleStatus

TRAIN_KINDS = ("priority", "train")
WARNING_KINDS = ("rest", "reduce", "enough")


@dataclass(frozen=True)
class MuscleGuidance:
    muscle: str
    kind: str
    reasons: Tuple[str, ...]  # i18n keys, most important first
    suggested_sets: int


@dataclass(frozen=True)
class Guidance:
    verdict: str
    accumulated_fatigue: bool
    muscles: Tuple[MuscleGuidance, ...]
    warnings: Tuple[MuscleGuidance, ...]


def muscle_kind(plan: MusclePlan, status: MuscleStatus) -> Optional[str]:
    if plan.action == "rest":
        return "rest"
    if status.volume_zone == "above":
        return "enough"
    if plan.action == "reduce_volume":
        return "reduce"
    if plan.targeted and status.volume_zone == "below":
        return "priority"
    if plan.targeted or plan.allocated_sets > 0:
        return "train"
    return None


def build_guidance(
    plans: Sequence[MusclePlan],
    statuses: Mapping[str, MuscleStatus],
    has_history: bool,
) -> Guidance:
    if not has_history:
        return Guidance("no_history", False, (), ())

    # ``plans`` is already in Stage 1 priority order; sorted() is stable.
    items = []
    for plan in plans:
        status = statuses.get(plan.muscle)
        if status is None or not status.major:
            continue
        kind = muscle_kind(plan, status)
        if kind is None:
            continue
        sets = plan.allocated_sets if kind in TRAIN_KINDS else 0
        # A muscle that should rest gets only the recovery reason: "too few
        # sets" next to "let it rest" would read as a contradiction.
        reasons = plan.reasons[:1] if kind == "rest" else plan.reasons[:2]
        items.append(MuscleGuidance(plan.muscle, kind, reasons, sets))

    to_train = sorted(
        (i for i in items if i.kind in TRAIN_KINDS), key=lambda i: TRAIN_KINDS.index(i.kind)
    )
    warnings = sorted(
        (i for i in items if i.kind in WARNING_KINDS), key=lambda i: WARNING_KINDS.index(i.kind)
    )
    major = [s for s in statuses.values() if s.major]
    accumulated = any(s.accumulated_fatigue for s in major)
    # Local fatigue in some muscles is a warning, not a rest day: the whole
    # day is "rest" only when no major muscle is ready.
    none_ready = bool(major) and all(
        s.readiness_level in ("low", "moderate") or s.accumulated_fatigue for s in major
    )

    if any(i.kind == "priority" for i in to_train):
        verdict = "focus"
    elif to_train:
        verdict = "train"
    elif none_ready:
        verdict = "rest"
    else:
        verdict = "balanced"

    return Guidance(
        verdict=verdict,
        accumulated_fatigue=accumulated,
        muscles=tuple(to_train[: P.GUIDANCE_MAX_MUSCLES]),
        warnings=tuple(warnings[: P.GUIDANCE_MAX_WARNINGS]),
    )
