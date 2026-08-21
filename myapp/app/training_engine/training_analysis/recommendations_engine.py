from datetime import date
from typing import List, Mapping, Any, Set

from myapp.app.training_engine.models.exercise import Exercise

from myapp.app.training_engine.training_analysis.dto import (
    RecommendationPackage,
    RecommendationExercise,
    MuscleResult,
    PatternResult,
    ProgressionResult,
    DiversityResult,
    FrequencyResult,
)

from myapp.app.training_engine.training_analysis.analyzers.muscles import (
    analyse_muscles,
)

from myapp.app.training_engine.training_analysis.analyzers.patterns import (
    analyse_patterns,
)

from myapp.app.training_engine.training_analysis.analyzers.progression import (
    analyse_progression,
)

from myapp.app.training_engine.training_analysis.analyzers.load import (
    analyse_load,
)

from myapp.app.training_engine.training_analysis.analyzers.recovery import (
    analyse_recovery,
)

from myapp.app.training_engine.training_analysis.analyzers.diversity import (
    analyse_diversity,
)

from myapp.app.training_engine.training_analysis.analyzers.frequency import (
    analyse_frequency,
)

from myapp.app.training_engine.training_analysis.analyzers.utils import (
    pattern_key,
    primary_muscles,
    movement_pattern,
)

from myapp.app.training_engine.training_analysis.constants import (
    WEAK_MUSCLE_SCORE,
    OVERLOAD_PENALTY,
    PATTERN_SCORE,
    PATTERN_OVERLOAD_PENALTY,
    DIFFICULTY_PENALTY,
    RISK_PENALTY,
    DIVERSITY_BONUS,
    REPEATED_EXERCISE_PENALTY,
    FREQUENCY_HIGH,
    FREQUENCY_LOW,
    FREQUENCY_PENALTY,
    FREQUENCY_BONUS,
    PROGRESSION_SCORE,
    PLATEAU_SCORE,
    REGRESSION_SCORE,
    RECOVERY_PENALTY,
    RECOVERY_MODERATE_PENALTY,
    USER_LEVEL_BEGINNER,
    USER_LEVEL_INTERMEDIATE,
    USER_LEVEL_ADVANCED,
    PROFILE_WEAK_SCORE,
    PROFILE_STRONG_PENALTY,
    MIN_RECOMMENDATION_SCORE,
    MAX_RECOMMENDATIONS,
    SUMMARY_PRIORITY,
    PROGRESSION_PLATEAU_THRESHOLD,
)


def _normalize_user_level(user: Any) -> str:
    raw = (
        getattr(user, "experience", None)
        or getattr(user, "level", None)
        or USER_LEVEL_INTERMEDIATE
    )

    value = str(raw).strip().lower()

    mapping = {
        "beginner": USER_LEVEL_BEGINNER,
        "початківець": USER_LEVEL_BEGINNER,
        "початковий": USER_LEVEL_BEGINNER,
        "intermediate": USER_LEVEL_INTERMEDIATE,
        "середній": USER_LEVEL_INTERMEDIATE,
        "advanced": USER_LEVEL_ADVANCED,
        "досвідчений": USER_LEVEL_ADVANCED,
        "просунутий": USER_LEVEL_ADVANCED,
    }

    return mapping.get(value, USER_LEVEL_INTERMEDIATE)


def _profile_points(user: Any, key: str) -> Set[str]:
    raw = getattr(user, key, None)

    if not raw:
        return set()

    if isinstance(raw, str):
        raw = raw.split(",")

    if not isinstance(raw, (list, tuple, set)):
        return set()

    return {str(value).strip().lower() for value in raw if str(value).strip()}


def _exercise_history_count(
    ex: Exercise,
    sessions: List,
) -> int:
    count = 0

    for session in sessions:
        for session_exercise in session.exercises or []:
            if session_exercise.exercise_id == ex.id:
                count += 1

    return count


def _reason_muscles(
    ex: Exercise,
    muscles: MuscleResult,
) -> List[str]:
    reasons: List[str] = []
    primary = set(primary_muscles(ex))

    if primary.intersection(muscles["weak"]):
        reasons.append("improves weak muscle group")

    return reasons


def _reason_profile(
    ex: Exercise,
    weak_points: Set[str],
) -> List[str]:
    primary = set(primary_muscles(ex))

    if primary.intersection(weak_points):
        return ["targets your weak point"]

    return []


def _reason_patterns(
    ex: Exercise,
    patterns: PatternResult,
) -> List[str]:
    movement = movement_pattern(ex)

    if movement in patterns["weak_patterns"]:
        return ["improves weak movement pattern"]

    return []


def _reason_progression(
    ex: Exercise,
    progression: ProgressionResult,
) -> List[str]:
    details = progression["details"].get(str(ex.id))

    if not details:
        return []

    change = details["change"]

    if change < 0:
        return ["helps reverse regression"]

    if abs(change) < PROGRESSION_PLATEAU_THRESHOLD:
        return ["helps break plateau"]

    return []


def _reason_frequency(
    ex: Exercise,
    frequency: FrequencyResult,
) -> List[str]:
    counts = frequency["counts"]

    if not counts:
        return []

    for muscle in primary_muscles(ex):
        if counts.get(muscle, 0) <= FREQUENCY_LOW:
            return ["supports an undertrained muscle"]

    return []


def _reason_diversity(
    diversity: DiversityResult,
) -> List[str]:
    if diversity["status"] == "low":
        return ["adds exercise variety"]

    return []


def _reasons(
    ex: Exercise,
    muscles: MuscleResult,
    patterns: PatternResult,
    progression: ProgressionResult,
    frequency: FrequencyResult,
    diversity: DiversityResult,
    weak_points: Set[str],
) -> List[str]:
    reasons: List[str] = []

    reasons.extend(_reason_profile(ex, weak_points))
    reasons.extend(_reason_muscles(ex, muscles))
    reasons.extend(_reason_patterns(ex, patterns))
    reasons.extend(_reason_progression(ex, progression))
    reasons.extend(_reason_frequency(ex, frequency))
    reasons.extend(_reason_diversity(diversity))

    return list(dict.fromkeys(reasons))


def _score_muscles(
    ex: Exercise,
    muscles: MuscleResult,
) -> float:
    score = 0.0
    primary = set(primary_muscles(ex))

    weak_matches = primary.intersection(muscles["weak"])
    overloaded_matches = primary.intersection(muscles["overloaded"])

    score += len(weak_matches) * WEAK_MUSCLE_SCORE
    score -= len(overloaded_matches) * OVERLOAD_PENALTY

    return score


def _score_profile(
    ex: Exercise,
    weak_points: Set[str],
    strong_points: Set[str],
) -> float:
    primary = set(primary_muscles(ex))

    weak_matches = primary.intersection(weak_points)
    strong_matches = primary.intersection(strong_points)

    score = 0.0

    score += len(weak_matches) * PROFILE_WEAK_SCORE
    score -= len(strong_matches) * PROFILE_STRONG_PENALTY

    return score


def _score_patterns(
    ex: Exercise,
    patterns: PatternResult,
) -> float:
    movement = movement_pattern(ex)

    if movement in patterns["overloaded_patterns"]:
        return -PATTERN_OVERLOAD_PENALTY

    if movement in patterns["weak_patterns"]:
        return PATTERN_SCORE

    return 0.0


def _score_frequency(
    ex: Exercise,
    frequency: FrequencyResult,
) -> float:
    if not frequency["counts"]:
        return 0.0

    score = 0.0

    for muscle in primary_muscles(ex):
        count = frequency["counts"].get(muscle, 0)

        if count >= FREQUENCY_HIGH:
            score -= FREQUENCY_PENALTY

        elif count <= FREQUENCY_LOW:
            score += FREQUENCY_BONUS

    return score


def _score_progression(
    ex: Exercise,
    progression: ProgressionResult,
) -> float:
    details = progression["details"].get(str(ex.id))

    if not details:
        return 0.0

    change = details["change"]

    if change < 0:
        return REGRESSION_SCORE

    if abs(change) < PROGRESSION_PLATEAU_THRESHOLD:
        return PLATEAU_SCORE

    if change > 0.15:
        return PROGRESSION_SCORE

    return 0.0


def _score_difficulty(
    ex: Exercise,
    user_level: str,
) -> float:
    difficulty = float(ex.difficulty or 1)

    if user_level == USER_LEVEL_BEGINNER and difficulty >= 4:
        return -DIFFICULTY_PENALTY

    if user_level == USER_LEVEL_ADVANCED and difficulty <= 1:
        return 0.5

    return 0.0


def _score_risk(
    ex: Exercise,
    user_level: str,
) -> float:
    risk = float(ex.risk_level or 1)

    if user_level == USER_LEVEL_BEGINNER and risk >= 3:
        return -RISK_PENALTY

    return 0.0


def _score_recovery(
    recovery_status: str,
    ex: Exercise,
    muscles: MuscleResult,
) -> float:
    if recovery_status == "good":
        return 0.0

    primary = set(primary_muscles(ex))
    overloaded = set(muscles["overloaded"])

    if primary.intersection(overloaded):
        return -RECOVERY_PENALTY

    if recovery_status == "low":
        return -RECOVERY_MODERATE_PENALTY

    return 0.0


def _score_diversity(
    diversity: DiversityResult,
) -> float:
    if diversity["status"] == "low":
        return DIVERSITY_BONUS

    return 0.0


def _score_exercise(
    ex: Exercise,
    muscles: MuscleResult,
    patterns: PatternResult,
    progression: ProgressionResult,
    frequency: FrequencyResult,
    diversity: DiversityResult,
    recovery_status: str,
    user_level: str,
    sessions: List,
    weak_points: Set[str],
    strong_points: Set[str],
) -> float:
    score = 0.0

    score += _score_profile(
        ex,
        weak_points,
        strong_points,
    )

    score += _score_muscles(
        ex,
        muscles,
    )

    score += _score_patterns(
        ex,
        patterns,
    )

    score += _score_frequency(
        ex,
        frequency,
    )

    score += _score_progression(
        ex,
        progression,
    )

    score += _score_difficulty(
        ex,
        user_level,
    )

    score += _score_risk(
        ex,
        user_level,
    )

    score += _score_recovery(
        recovery_status,
        ex,
        muscles,
    )

    score += _score_diversity(
        diversity,
    )

    history_count = _exercise_history_count(
        ex,
        sessions,
    )

    if history_count >= FREQUENCY_HIGH:
        score -= REPEATED_EXERCISE_PENALTY

    return score


def _should_exclude(
    ex: Exercise,
    muscles: MuscleResult,
    patterns: PatternResult,
    recovery_status: str,
    user_level: str,
) -> bool:
    primary = set(primary_muscles(ex))
    movement = movement_pattern(ex)

    if primary.intersection(muscles["overloaded"]):
        return True

    if movement in patterns["overloaded_patterns"]:
        return True

    if (
        recovery_status == "low"
        and user_level == USER_LEVEL_BEGINNER
        and float(ex.risk_level or 1) >= 3
    ):
        return True

    return False


def _build_summary(
    muscles: MuscleResult,
    load,
    recovery,
    patterns: PatternResult,
) -> str:
    messages = []

    if recovery["status"] == "low":
        messages.append(("recovery", "recovery should be prioritized"))

    if load["status"] in {"hard", "very_hard"}:
        messages.append(("load", "training load is high"))

    if muscles["weak"]:
        messages.append(("muscles", "some muscle groups need more attention"))

    if patterns["weak_patterns"]:
        messages.append(("patterns", "some movement patterns need more work"))

    if not messages:
        return "training looks balanced."

    messages.sort(
        key=lambda item: SUMMARY_PRIORITY[item[0]],
        reverse=True,
    )

    return ". ".join(message for _, message in messages) + "."


def build_recommendations(
    user: Any,
    sessions: List,
    target_day: date,
) -> RecommendationPackage:
    exercises: List[Exercise] = Exercise.query.all()

    exercise_map: Mapping[object, Exercise] = {
        exercise.id: exercise for exercise in exercises
    }

    weight = float(getattr(user, "weight", 70) or 70)

    user_level = _normalize_user_level(user)

    weak_points = _profile_points(
        user,
        "weak_points",
    )

    strong_points = _profile_points(
        user,
        "strong_points",
    )

    muscles = analyse_muscles(
        sessions,
        target_day,
    )

    patterns = analyse_patterns(
        sessions,
        target_day,
        exercise_map,
        user_weight=weight,
    )

    progression = analyse_progression(
        sessions,
        target_day,
        exercise_map,
        user_weight=weight,
    )

    load = analyse_load(
        sessions,
        target_day,
    )

    recovery = analyse_recovery(
        user,
        sessions,
        target_day,
    )

    diversity = analyse_diversity(
        sessions,
        target_day,
        exercise_map,
    )

    frequency = analyse_frequency(
        sessions,
        target_day,
        exercise_map,
    )

    scored: List[tuple[float, Exercise]] = []

    for exercise in exercises:
        if not exercise.muscles_primary:
            continue

        if _should_exclude(
            exercise,
            muscles,
            patterns,
            recovery["status"],
            user_level,
        ):
            continue

        score = _score_exercise(
            exercise,
            muscles,
            patterns,
            progression,
            frequency,
            diversity,
            recovery["status"],
            user_level,
            sessions,
            weak_points,
            strong_points,
        )

        if score >= MIN_RECOMMENDATION_SCORE:
            scored.append((score, exercise))

    scored.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    recommended: List[RecommendationExercise] = []

    used_patterns = set()
    used_muscles = set()

    for score, exercise in scored:
        movement = pattern_key(exercise.movement_pattern)

        primary = set(primary_muscles(exercise))

        if movement in used_patterns:
            continue

        if primary.intersection(used_muscles):
            continue

        reasons = _reasons(
            exercise,
            muscles,
            patterns,
            progression,
            frequency,
            diversity,
            weak_points,
        )

        if not reasons:
            continue

        recommended.append(
            {
                "exercise": exercise.name,
                "reasons": reasons[:2],
                "score": round(score, 1),
            }
        )

        used_patterns.add(movement)
        used_muscles.update(primary)

        if len(recommended) >= MAX_RECOMMENDATIONS:
            break

    summary = _build_summary(
        muscles,
        load,
        recovery,
        patterns,
    )

    return {
        "load": load,
        "muscles": muscles,
        "patterns": patterns,
        "progression": progression,
        "recovery": recovery,
        "diversity": diversity,
        "frequency": frequency,
        "recommended_exercises": recommended,
        "summary": summary,
    }
