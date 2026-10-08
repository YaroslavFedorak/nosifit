"""User-facing representation of a TrainingAnalysis.

Raw physiological values stay internal; the payload exposes levels, states,
rounded weekly set counts with their target bands, and reason keys.
The top-level keys of /api/training/recommendations are kept compatible.
"""

import math
from collections import defaultdict
from datetime import timedelta
from typing import Dict, List

from . import parameters as P
from .selection import pattern_family
from .service import TrainingAnalysis
from .status import statuses_by_state

SUMMARY = "recommendations.training.summary."


def _round_half(value: float) -> float:
    return round(value * 2) / 2.0


def muscle_status_payload(analysis: TrainingAnalysis) -> List[Dict]:
    plans = {plan.muscle: plan for plan in analysis.plans}
    order = {muscle: index for index, muscle in enumerate(P.MAJOR_MUSCLES)}
    items = []
    for muscle, status in sorted(
        analysis.statuses.items(), key=lambda kv: (order.get(kv[0], len(order)), kv[0])
    ):
        plan = plans.get(muscle)
        items.append(
            {
                "muscle": muscle,
                "major": status.major,
                "state": status.state,
                "readiness": status.readiness_level,
                "readiness_score": round(status.readiness_score, 2),
                "weekly_sets": _round_half(status.exposure_smoothed),
                "average_weekly_sets": _round_half(status.exposure_long),
                "target": (
                    {"lower": status.lower_target, "upper": status.upper_target}
                    if status.major
                    else None
                ),
                "trend": status.trend,
                "action": plan.action if plan else "maintain",
                "suggested_sets": plan.allocated_sets if plan and plan.action in ("prioritize", "train") else 0,
                "reasons": list(plan.reasons) if plan else [],
            }
        )
    return items


def _muscles_section(analysis: TrainingAnalysis) -> Dict:
    statuses = analysis.statuses
    major = {m: s for m, s in statuses.items() if s.major}
    weak = statuses_by_state(major, "underloaded")
    overloaded = statuses_by_state(statuses, "high_fatigue", "accumulated_fatigue")
    balanced = sorted(
        m for m, s in major.items()
        if s.volume_zone == "within" and s.state in ("appropriate", "recovery_available")
    )
    totals = {
        m: round(s.exposure_smoothed, 1)
        for m, s in statuses.items()
        if s.exposure_smoothed >= P.DISPLAY_MIN_SETS
    }
    ratio = {
        m: round(s.exposure_smoothed / ((s.lower_target + s.upper_target) / 2.0), 2)
        for m, s in major.items()
    }
    return {
        "weak": weak,
        "overloaded": overloaded,
        "balanced": balanced,
        "totals": totals,
        "balance_ratio": ratio,
        "message": "muscle status analysed" if analysis.doses else "no muscle data",
    }


def _patterns_section(analysis: TrainingAnalysis) -> Dict:
    sets = defaultdict(float)
    for dose in analysis.doses:
        family = pattern_family(analysis.catalog[dose.exercise_id])
        weight = math.exp(
            -((analysis.now - dose.performed_at).total_seconds() / 86400.0)
            / P.EXPOSURE_RECENT_TAU_DAYS
        )
        sets[family] += dose.stimulus_sets * weight * 7.0 / P.EXPOSURE_RECENT_TAU_DAYS
    return {
        "pattern_sets": {k: round(v, 1) for k, v in sorted(sets.items()) if v >= P.DISPLAY_MIN_SETS},
        "message": "movement patterns analysed" if sets else "no pattern data",
    }


def _window(analysis: TrainingAnalysis, days: int):
    start = analysis.now - timedelta(days=days)
    return [d for d in analysis.doses if d.performed_at >= start]


def _load_section(analysis: TrainingAnalysis) -> Dict:
    recent = _window(analysis, P.SUMMARY_WINDOW_DAYS)
    rated = [P.RPE_TO_RIR_OFFSET - d.rir for d in recent if d.rated]
    return {
        "hard_sets_7d": round(sum(d.stimulus_sets for d in recent), 1),
        "session_training_stress_proxy_7d": round(sum(d.fatigue_sets for d in recent), 1),
        "sessions_count": len({d.session_id for d in recent}),
        "avg_rpe": round(sum(rated) / len(rated), 2) if rated else None,
        "message": "training volume analysed" if recent else "no load data",
    }


def _recovery_section(analysis: TrainingAnalysis) -> Dict:
    statuses = analysis.statuses.values()
    trained = [s for s in statuses if s.days_since_trained is not None and s.days_since_trained <= P.SUMMARY_WINDOW_DAYS]
    low = sorted(s.muscle for s in trained if s.readiness_level in ("low", "moderate"))
    modifier = next(iter(statuses)).sleep_modifier if analysis.statuses else 1.0
    if any(s.readiness_level == "low" or s.accumulated_fatigue for s in trained):
        level = "low"
    elif low:
        level = "moderate"
    else:
        level = "good"
    return {
        "status": level,
        "low_readiness_muscles": low,
        "sleep_affects_readiness": modifier < 1.0,
        "message": "readiness analysed",
    }


def _frequency_section(analysis: TrainingAnalysis) -> Dict:
    sessions = defaultdict(set)
    for dose in _window(analysis, P.FREQUENCY_WINDOW_DAYS):
        for muscle, sets in dose.muscle_stimulus:
            if sets >= P.DIRECT_EXPOSURE_MIN_SETS:
                sessions[muscle].add(dose.session_id)
    return {"counts": {m: len(v) for m, v in sorted(sessions.items())}, "message": "muscle frequency analysed"}


def _diversity_section(analysis: TrainingAnalysis) -> Dict:
    names = [d.exercise_id for d in _window(analysis, P.FREQUENCY_WINDOW_DAYS)]
    if not names:
        return {"status": "unknown", "unique_exercises": 0, "total_exercises": 0, "message": "no exercise data"}
    return {
        "unique_exercises": len(set(names)),
        "total_exercises": len(names),
        "message": "exercise diversity analysed",
    }


def _summary(analysis: TrainingAnalysis, recovery: Dict) -> str:
    statuses = analysis.statuses.values()
    if any(s.accumulated_fatigue for s in statuses):
        return SUMMARY + "highLoad"
    if recovery["status"] == "low":
        return SUMMARY + "recovery"
    if any(s.state == "underloaded" for s in statuses):
        return SUMMARY + "muscles"
    return SUMMARY + "balanced"


def recommendation_payload(analysis: TrainingAnalysis) -> Dict:
    recovery = _recovery_section(analysis)
    recommended = []
    for item in analysis.exercises:
        exercise = item.exercise
        recommended.append(
            {
                "exercise": exercise.name,
                "slug": exercise.slug,
                "measurement_type": exercise.measurement_type,
                "sets": item.sets,
                "reps": item.reps,
                "duration_sec": item.duration_sec,
                "per_side": item.per_side,
                "target_rir": f"{item.target_rir[0]}-{item.target_rir[1]}",
                "target_muscles": list(item.target_muscles),
                "reasons": list(item.reasons[:2]),
                "score": round(item.score, 2),
            }
        )
    return {
        "model_version": P.MODEL_VERSION,
        "load": _load_section(analysis),
        "muscles": _muscles_section(analysis),
        "muscle_status": muscle_status_payload(analysis),
        "patterns": _patterns_section(analysis),
        "progression": analysis.progression,
        "recovery": recovery,
        "diversity": _diversity_section(analysis),
        "frequency": _frequency_section(analysis),
        "recommended_exercises": recommended,
        "summary": _summary(analysis, recovery),
    }
