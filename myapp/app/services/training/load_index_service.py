from datetime import date, timedelta
from typing import Dict, List

from myapp.app.training_engine.models.fatigue_state import FatigueState
from myapp.app.training_engine.models.performance_state import PerformanceState
from myapp.app.models.training_session import TrainingSession
from myapp.app.training_engine.models.exercise import Exercise

# constants
CHRONIC_WINDOW_DAYS = 14

# weights for capacity vs history (base max values)
MAX_HISTORY_WEIGHT = 0.6
MIN_CAPACITY_WEIGHT = 0.4

# duration bonus (max +20%)
MAX_DURATION_BONUS = 0.2

# bodyweight ratios for some common exercises
BODYWEIGHT_RATIO = {
    "push-ups": 0.64,
    "pull-ups": 1.00,
    "bench-dips": 0.70,
    "dips": 0.87,
    "plank": 0.45,
    "wall-sit": 0.55,
    "burpee": 0.95,
    "jump-squat": 1.05,
    "lunge-bodyweight": 0.85,
    "squat-bodyweight": 0.90,
}


def _movement_factor(pattern: str) -> float:
    # simple movement pattern multiplier
    p = (pattern or "").lower()

    if "hinge" in p:
        return 1.20
    if "squat" in p:
        return 1.15
    if "pull" in p:
        return 1.10
    if "push" in p:
        return 1.05
    if "core" in p:
        return 0.75
    if "accessory" in p:
        return 0.85

    return 1.0


def _compound_factor(ex: Exercise) -> float:
    # count primary + secondary muscles
    primary = ex.muscles_primary or []
    secondary = ex.muscles_secondary or []
    count = len(primary) + len(secondary)

    if count <= 1:
        base = 0.9
    elif count == 2:
        base = 1.0
    elif count == 3:
        base = 1.15
    else:
        base = 1.25

    # soften effect so it does not explode
    return 1.0 + (base - 1.0) * 0.5


def _muscle_factor(ex: Exercise) -> float:
    # small bonus for more primary muscles
    primary = ex.muscles_primary or []
    base = 1.0 + len(primary) * 0.15
    # soften effect a bit
    return 1.0 + (base - 1.0) * 0.3


def _parse_int(value) -> int:
    # safe int parsing from db/json
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        digits = "".join(c for c in value if c.isdigit())
        if digits:
            return int(digits)
    return 0


def _parse_float(value) -> float:
    # safe float parsing from db/json
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        digits = "".join(c for c in value if c.isdigit() or c == ".")
        if digits:
            try:
                return float(digits)
            except ValueError:
                return 0.0
    return 0.0


def _parse_reps(reps) -> float:
    # reps may be "12", "8-12", "30", "45s", etc.
    if isinstance(reps, (int, float)):
        return float(reps)

    if isinstance(reps, str):
        r = reps.strip()

        if "-" in r:
            try:
                a, b = r.split("-")
                return (int(a) + int(b)) / 2.0
            except Exception:
                return 10.0

        if r.isdigit():
            return float(r)

        digits = "".join(c for c in r if c.isdigit())
        if digits:
            return float(digits)

    return 0.0


def _is_bodyweight(ex: Exercise) -> bool:
    # try to detect bodyweight exercises from equipment
    equipment = ex.equipment or []

    if isinstance(equipment, str):
        equipment = [equipment]

    normalized = [e.lower().replace(" ", "") for e in equipment]
    return "bodyweight" in normalized


def _relative_weight(ex: Exercise, load: float, user_weight: float) -> float:
    # relative load to user and exercise max
    if load > 0:
        rel_user = load / max(user_weight, 1.0)
        max_load = _parse_float(ex.max_additional_load_kg)
        rel_ex = load / max(max_load or user_weight, 1.0)

        # cap exercise-relative part to avoid crazy values
        rel_ex = min(rel_ex, 1.5)

        rw = 0.7 * rel_user + 0.3 * rel_ex
        # cap final rw a bit too
        rw = min(rw, 1.8)

        # small correction for pure bodyweight equipment
        if _is_bodyweight(ex):
            rw *= 0.9

        return rw

    # bodyweight-only case
    slug = (ex.slug or "").lower()
    if slug in BODYWEIGHT_RATIO:
        return BODYWEIGHT_RATIO[slug]

    mp = (ex.movement_pattern or "").lower()
    if "push" in mp:
        return 0.65
    if "pull" in mp:
        return 0.90
    if "accessory" in mp:
        return 0.40

    return 0.50


def _compute_volume(ex: Exercise, sets: int, reps: float) -> float:
    # normalize reps safely
    if isinstance(reps, str):
        # handle formats like "8-12"
        if "-" in reps:
            try:
                reps = float(reps.split("-")[0])
            except Exception:
                reps = 0.0
        else:
            try:
                reps = float(reps)
            except Exception:
                reps = 0.0
    else:
        try:
            reps = float(reps)
        except Exception:
            reps = 0.0

    # normalize sets
    try:
        sets = float(sets)
    except Exception:
        sets = 0.0

    # volume for normal and isometric exercises
    name = (ex.name or "").lower()

    if "планк" in name or "plank" in name or "wall sit" in name:
        seconds = reps if reps > 0 else 30.0
        # simple scaling for isometric work
        return float(sets) * ((seconds / 7.0) ** 0.85)

    # sublinear volume so high reps do not break the model
    reps = max(reps, 0.0)
    return float(sets) * (reps**0.85)


def _compute_exercise_load(
    ex: Exercise, sets: int, reps: float, load: float, user_weight: float
) -> float:
    # main per-exercise load formula
    volume = _compute_volume(ex, sets, reps)
    rw = _relative_weight(ex, load, user_weight)

    difficulty_raw = _parse_float(ex.difficulty)
    # clamp difficulty to sane range
    difficulty = min(max(difficulty_raw, 1.0), 5.0)
    diff = 0.9 + difficulty * 0.1

    move = _movement_factor(ex.movement_pattern or "")
    comp = _compound_factor(ex)
    muscle = _muscle_factor(ex)

    # keep formula mostly multiplicative but with softened factors
    load_value = volume * rw
    load_value *= diff
    load_value *= move
    load_value *= comp
    load_value *= muscle

    return float(load_value)


def _compute_session_load(session: TrainingSession, user, exercise_map) -> float:
    # sum load for all exercises in session
    weight = getattr(user, "weight", 70) or 70
    weight = float(weight)
    total = 0.0

    for se in session.exercises:
        ex = exercise_map.get(se.exercise_id)
        if not ex:
            continue

        raw_sets = se.sets_done or se.sets_planned or 0
        sets = _parse_int(raw_sets)

        raw_reps = se.reps_done or se.reps_planned or 0
        reps = _parse_reps(raw_reps)

        raw_load = se.load_done or se.load_planned or 0
        load = _parse_float(raw_load)

        total += _compute_exercise_load(ex, sets, reps, load, weight)

    if session.started_at and session.finished_at:
        duration_min = (session.finished_at - session.started_at).total_seconds() / 60.0
        # simple duration bonus, capped
        dur_factor = 1.0 + min(
            (duration_min / 120.0) * MAX_DURATION_BONUS, MAX_DURATION_BONUS
        )
        total *= dur_factor

    return float(total)


def _build_daily_loads(
    sessions: List[TrainingSession], user, exercise_map
) -> Dict[date, float]:
    # precompute daily loads so we do not recalc sessions twice
    daily_loads: Dict[date, float] = {}

    for s in sessions:
        if not s.started_at:
            continue

        d = s.started_at.date()
        day_total = daily_loads.get(d, 0.0)
        day_total += _compute_session_load(s, user, exercise_map)
        daily_loads[d] = day_total

    return daily_loads


def _compute_chronic_mean(daily_loads: Dict[date, float], target_day: date) -> float:
    # 14-day rolling mean including rest days
    values: List[float] = []

    for i in range(CHRONIC_WINDOW_DAYS):
        day = target_day - timedelta(days=i)
        values.append(daily_loads.get(day, 0.0))

    return sum(values) / float(CHRONIC_WINDOW_DAYS)


def _compute_capacity(user) -> float:
    # capacity from performance tests
    perf = user.performance_states.order_by(PerformanceState.created_at.desc()).first()
    if not perf:
        # default capacity if no tests yet
        return 120.0

    pushups = getattr(perf, "pushups", 0) or 0
    squats = getattr(perf, "squats", 0) or 0
    situps = getattr(perf, "situps", 0) or 0
    plank = getattr(perf, "plank_sec", 0) or 0
    weight = getattr(user, "weight", 70) or 70

    # simple weighted sum, can be tuned later
    strength = pushups * 1.0 + squats * 0.8 + situps * 0.6 + plank / 5.0

    # small normalization by bodyweight
    strength *= (float(weight) / 70.0) ** 0.1

    return float(strength)


def _min_reference_by_level(level: str) -> float:
    # minimal reference load by user level (can be tuned with data)
    if level == "Початківець":
        return 120.0
    if level == "Середній":
        return 170.0
    if level == "Досвідчений":
        return 220.0
    return 170.0


def _compute_history_capacity_weights(
    daily_loads: Dict[date, float], target_day: date
) -> tuple[float, float]:
    # dynamic weights based on how many training days user has
    history_days = sum(1 for load in daily_loads.values() if load > 0.0)

    # clamp days to window size
    days_factor = min(history_days / float(CHRONIC_WINDOW_DAYS), 1.0)

    history_weight = MAX_HISTORY_WEIGHT * days_factor
    capacity_weight = 1.0 - history_weight

    # do not let capacity weight go below some minimum
    capacity_weight = max(capacity_weight, MIN_CAPACITY_WEIGHT)
    history_weight = 1.0 - capacity_weight

    return float(capacity_weight), float(history_weight)


def _compute_fatigue_factor(
    user, daily_loads: Dict[date, float], target_day: date
) -> float:
    # fatigue from fatigue_state + recent training days
    fatigue = getattr(user, "fatigue_state", None)
    factor = 1.0

    if isinstance(fatigue, FatigueState):
        stress = getattr(fatigue, "stress", 0) or 0
        soreness = getattr(fatigue, "soreness", 0) or 0
        sleep = getattr(fatigue, "sleep", 7) or 7

        factor *= 1.0 + (stress + soreness) * 0.02
        factor *= 1.0 - max(0, (8 - sleep)) * 0.015

    # count recent training days (last 3 days, excluding today)
    recent_days = 0
    for i in range(1, 4):
        d = target_day - timedelta(days=i)
        if daily_loads.get(d, 0.0) > 0.0:
            recent_days += 1

    # small extra fatigue for back-to-back training
    factor *= 1.0 + recent_days * 0.03

    # clamp fatigue factor to safe range
    factor = max(0.7, min(factor, 1.3))

    return float(factor)


def compute_daily_load_index(
    user, sessions: List[TrainingSession], target_day: date
) -> Dict:
    # main public API for daily load index
    exercise_map = {ex.id: ex for ex in Exercise.query.all()}

    # build daily loads once
    daily_loads = _build_daily_loads(sessions, user, exercise_map)

    # load for target day from precomputed dict
    load_today = daily_loads.get(target_day, 0.0)

    if load_today <= 0.0:
        return {
            "percent": 0,
            "raw_percent": 0.0,
            "level": 0,
            "load_today": 0.0,
            "reference_load": 0.0,
            "capacity": 0.0,
            "chronic_mean": 0.0,
            "fatigue_factor": 1.0,
        }

    chronic_mean = _compute_chronic_mean(daily_loads, target_day)
    capacity = _compute_capacity(user)

    capacity_weight, history_weight = _compute_history_capacity_weights(
        daily_loads, target_day
    )

    reference_load = capacity_weight * capacity + history_weight * chronic_mean
    reference_load = max(
        reference_load, _min_reference_by_level(getattr(user, "level", "Середній"))
    )

    fatigue_factor = _compute_fatigue_factor(user, daily_loads, target_day)

    adjusted = load_today * fatigue_factor
    raw_percent = (adjusted / max(reference_load, 1.0)) * 100.0

    # clamp display percent but keep raw_percent for internal use
    percent = int(max(0.0, min(raw_percent, 150.0)))

    if percent < 20:
        level = 0
    elif percent < 40:
        level = 1
    elif percent < 60:
        level = 2
    elif percent < 80:
        level = 3
    else:
        level = 4

    return {
        "percent": percent,
        "raw_percent": float(raw_percent),
        "level": level,
        "load_today": float(load_today),
        "reference_load": float(reference_load),
        "capacity": float(capacity),
        "chronic_mean": float(chronic_mean),
        "fatigue_factor": float(fatigue_factor),
    }
