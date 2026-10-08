"""Exercise stimulus -> muscle stimulus, and the separate fatigue cost.

    exercise profile (catalog muscle_load_profile)
          |
    contribution weighting   (contribution_weights)
          |
    effective muscle stimulus (muscle_stimulus)   and   muscle fatigue cost

Stimulus and fatigue are computed side by side but never mixed: stimulus
feeds historical exposure, fatigue feeds readiness.
"""

import math
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from . import parameters as P
from .numeric import clamp, sigmoid, smoothstep
from .records import ExerciseInfo, LoggedEntry


def effective_rir(rpe: Optional[float]) -> Tuple[float, bool]:
    """Operational RIR from a logged RPE; (DEFAULT_RIR, False) when unrated."""
    if rpe is None:
        return P.DEFAULT_RIR, False
    try:
        value = float(rpe)
    except (TypeError, ValueError):
        return P.DEFAULT_RIR, False
    if not math.isfinite(value) or value <= 0:
        return P.DEFAULT_RIR, False
    return clamp(P.RPE_TO_RIR_OFFSET - value, P.RIR_MIN, P.RIR_MAX), True


def set_stimulus(rir: float) -> float:
    """Stimulus of one set relative to a set taken to failure, in (0, 1]."""
    rir = clamp(rir, P.RIR_MIN, P.RIR_MAX)
    scale = sigmoid(P.RIR_STIMULUS_MIDPOINT / P.RIR_STIMULUS_WIDTH)
    return sigmoid((P.RIR_STIMULUS_MIDPOINT - rir) / P.RIR_STIMULUS_WIDTH) / scale


def set_fatigue_cost(rir: float) -> float:
    """Fatigue of one set: its stimulus plus a premium that grows near failure."""
    rir = clamp(rir, P.RIR_MIN, P.RIR_MAX)
    premium = P.FAILURE_FATIGUE_EXTRA * math.exp(-rir / P.FAILURE_FATIGUE_RIR_DECAY)
    return set_stimulus(rir) * (1.0 + premium)


def novelty_multiplier(days_since_last: Optional[float]) -> float:
    """Extra fatigue of an unfamiliar exercise, rising smoothly with the gap."""
    if days_since_last is None:
        return P.NOVELTY_MAX_MULTIPLIER
    progress = smoothstep(P.NOVELTY_FAMILIAR_DAYS, P.NOVELTY_UNFAMILIAR_DAYS, days_since_last)
    return 1.0 + (P.NOVELTY_MAX_MULTIPLIER - 1.0) * progress


def is_training_exercise(exercise: ExerciseInfo) -> bool:
    return exercise.movement_pattern not in P.NON_TRAINING_PATTERNS


def contribution_weights(exercise: ExerciseInfo) -> Dict[str, float]:
    """Per-muscle set weight of one set of ``exercise`` (heuristic normalisation).

    The catalog profile is a distribution of the exercise between muscles. It
    becomes set weights by dividing by the largest share; secondary muscles are
    capped at INDIRECT_SET_CAP. Exercises without a profile fall back to the
    primary/secondary lists (1.0 / cap).
    """
    if not is_training_exercise(exercise):
        return {}

    if exercise.profile:
        top = max(share for _, share in exercise.profile)
        weights = {}
        for muscle, share in exercise.profile:
            ratio = share / top
            if muscle not in exercise.primary:
                ratio = min(ratio, P.INDIRECT_SET_CAP)
            weights[muscle] = ratio
        return weights

    weights = {muscle: 1.0 for muscle in exercise.primary}
    for muscle in exercise.secondary:
        weights.setdefault(muscle, P.INDIRECT_SET_CAP)
    return weights


@dataclass(frozen=True)
class Dose:
    """What one logged exercise did: stimulus and fatigue, overall and per muscle."""

    session_id: Optional[int]
    exercise_id: str
    performed_at: object  # datetime
    sets: int
    rir: float
    rated: bool
    stimulus_sets: float
    fatigue_sets: float
    novelty: float
    muscle_stimulus: Tuple[Tuple[str, float], ...]
    muscle_fatigue: Tuple[Tuple[str, float], ...]
    volume_load_kg: float
    heavy_sets: int


def entry_dose(
    entry: LoggedEntry,
    exercise: ExerciseInfo,
    days_since_last: Optional[float],
    body_weight_kg: Optional[float] = None,
) -> Dose:
    sets = max(int(entry.sets or 0), 0)
    rir, rated = effective_rir(entry.rpe)
    training = is_training_exercise(exercise)

    stimulus_sets = sets * set_stimulus(rir) if training else 0.0
    novelty = novelty_multiplier(days_since_last)
    fatigue_sets = sets * set_fatigue_cost(rir) * novelty if training else 0.0

    weights = contribution_weights(exercise)
    muscle_stimulus = tuple(sorted((m, stimulus_sets * w) for m, w in weights.items()))
    muscle_fatigue = tuple(sorted((m, fatigue_sets * w) for m, w in weights.items()))

    return Dose(
        session_id=entry.session_id,
        exercise_id=entry.exercise_id,
        performed_at=entry.performed_at,
        sets=sets,
        rir=rir,
        rated=rated,
        stimulus_sets=stimulus_sets,
        fatigue_sets=fatigue_sets,
        novelty=novelty,
        muscle_stimulus=muscle_stimulus,
        muscle_fatigue=muscle_fatigue,
        volume_load_kg=volume_load_kg(entry, exercise, body_weight_kg),
        heavy_sets=heavy_set_count(entry, rir),
    )


def volume_load_kg(entry: LoggedEntry, exercise: ExerciseInfo, body_weight_kg: Optional[float]) -> float:
    """Tonnage (sets x reps x kg). Descriptive only; never used as stimulus."""
    if entry.reps is None or entry.reps <= 0 or entry.sets <= 0:
        return 0.0
    kg = max(entry.load_kg or 0.0, 0.0)
    if exercise.load_type == "bodyweight" and body_weight_kg and exercise.bodyweight_ratio:
        kg += body_weight_kg * exercise.bodyweight_ratio
    return entry.sets * entry.reps * kg


def heavy_set_count(entry: LoggedEntry, rir: float) -> int:
    """Strength-relevant sets: reps + RIR within ~6RM (needs reps)."""
    if entry.reps is None or entry.reps <= 0:
        return 0
    if entry.reps + rir <= P.HEAVY_SET_MAX_REPS_TO_FAILURE:
        return max(int(entry.sets or 0), 0)
    return 0
