from typing import TypedDict, List, Dict


class MuscleResult(TypedDict):
    weak: List[str]
    overloaded: List[str]
    balanced: List[str]
    totals: Dict[str, float]
    balance_ratio: Dict[str, float]
    message: str


class PatternResult(TypedDict):
    weak_patterns: List[str]
    overloaded_patterns: List[str]
    pattern_loads: Dict[str, float]
    message: str


class ProgressionDetails(TypedDict):
    baseline_avg: float
    current_avg: float
    change: float


class ProgressionResult(TypedDict):
    status: str
    details: Dict[str, ProgressionDetails]
    message: str


class LoadResult(TypedDict):
    status: str
    avg_rpe: float
    sessions_count: int
    message: str


class RecoveryResult(TypedDict):
    status: str
    sleep_hours_avg: float
    fatigue_avg: float
    stress_avg: float
    soreness_avg: float
    message: str


class DiversityResult(TypedDict):
    status: str
    score: float
    unique_exercises: int
    total_exercises: int
    message: str


class FrequencyResult(TypedDict):
    counts: Dict[str, int]
    message: str


class RecommendationExercise(TypedDict):
    exercise: str
    reasons: List[str]
    score: float


class RecommendationPackage(TypedDict):
    load: LoadResult
    muscles: MuscleResult
    patterns: PatternResult
    progression: ProgressionResult
    recovery: RecoveryResult
    diversity: DiversityResult
    frequency: FrequencyResult
    recommended_exercises: List[RecommendationExercise]
    summary: str
