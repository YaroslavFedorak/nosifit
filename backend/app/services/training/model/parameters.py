"""Every coefficient of the training model, in one place.

The model is evidence-informed and heuristic: research guides its structure
and the direction of effects, while many values are engineering assumptions.

Each value is a ``Param`` that records what it is for and how much of it is
evidence versus engineering choice:

* ``heuristic=False`` - the value (or mapping) is taken from, or directly
  informed by, published evidence.
* ``heuristic=True``  - an engineering assumption chosen to make the model
  behave plausibly and stably. Evidence may inform its direction or order of
  magnitude, but not the number itself.

The model is decision support, not a physiological measurement. Nothing here
should be read as an individually measured quantity.

References (short form; full list in docs/training-model.md):
  Pelland 2024/2026  - weekly volume & frequency meta-regressions (SportRxiv 460)
  Robinson 2024      - proximity-to-failure meta-regressions, Sports Med 54:2209
  Refalo 2023        - failure vs non-failure hypertrophy, Sports Med 53:649
  Zourdos 2016       - RIR-based RPE scale, JSCR 30:267
  Halperin 2022      - accuracy of predicting reps to failure, Sports Med
  Moran-Navarro 2017 - recovery after failure vs non-failure, EJAP 117:2387
  Hyldahl 2017       - repeated bout effect, Exerc Sport Sci Rev 45:24
  Schoenfeld 2017    - weekly sets dose-response, J Sports Sci
  Baz-Valle 2022     - 12-20 weekly sets in trained men, J Hum Kinet 81:199
  Spiering 2021      - minimal dose for maintenance, JSCR
  ACSM 2026          - resistance training position stand, MSSE
  Remmert 2025       - per-session volume (SportRxiv 537, preprint)
  Knowles 2018 / Craven 2022 - sleep loss and strength performance
  Watson 2015        - AASM/SRS consensus: adults need >= 7 h sleep
"""

from dataclasses import dataclass
from typing import Any, Dict, Tuple

EVIDENCE_INFORMED = "evidence-informed"


@dataclass(frozen=True)
class Param:
    name: str
    value: Any
    unit: str
    purpose: str
    evidence: str
    confidence: str  # "high" | "moderate" | "low" | "n/a"
    heuristic: bool


REGISTRY: Dict[str, Param] = {}


def _param(name, value, unit, purpose, evidence, confidence, heuristic) -> Any:
    REGISTRY[name] = Param(name, value, unit, purpose, evidence, confidence, heuristic)
    return value


# --- Effort: RPE / RIR -------------------------------------------------------

RPE_TO_RIR_OFFSET = _param(
    "RPE_TO_RIR_OFFSET", 10.0, "RPE points",
    "Operational mapping RIR = 10 - RPE on the RIR-based RPE scale. It converts "
    "the logged rating; it is not a claim about the true reps left.",
    "Zourdos 2016; Helms 2016. Self-rated RIR carries ~1 rep individual error "
    "(Halperin 2022).",
    "moderate", heuristic=False,
)
RIR_MIN = _param("RIR_MIN", 0.0, "RIR", "Lower clamp of RIR.", "Definition.", "n/a", False)
RIR_MAX = _param(
    "RIR_MAX", 10.0, "RIR",
    "Upper clamp of RIR; beyond this a set is treated as very easy.",
    "Scale range of the RIR-based RPE scale.", "n/a", False,
)
DEFAULT_RIR = _param(
    "DEFAULT_RIR", 3.0, "RIR",
    "Effort assumed when no RPE was logged. Keeps unrated sets meaningful "
    "without pretending they were close to failure.",
    "Informed by Halperin 2022 (people underpredict reps left by ~1).",
    "low", heuristic=True,
)

# --- Stimulus: proximity to failure ----------------------------------------

RIR_STIMULUS_MIDPOINT = _param(
    "RIR_STIMULUS_MIDPOINT", 6.0, "RIR",
    "Centre of the sigmoid s(RIR): the RIR at which a set gives ~half of the "
    "stimulus of a set to failure.",
    "Direction (closer to failure -> more hypertrophy, saturating) from "
    "Robinson 2024 and Refalo 2023; the curve shape is an engineering choice.",
    "low", heuristic=True,
)
RIR_STIMULUS_WIDTH = _param(
    "RIR_STIMULUS_WIDTH", 2.0, "RIR",
    "Width of the sigmoid s(RIR); controls how gradually stimulus falls with RIR.",
    "Engineering choice keeping neighbouring RIR values within ~0.13 of each other.",
    "low", heuristic=True,
)

# --- Fatigue cost of a set ---------------------------------------------------

FAILURE_FATIGUE_EXTRA = _param(
    "FAILURE_FATIGUE_EXTRA", 1.0, "multiplier",
    "Extra fatigue of sets near failure: c(r) = s(r) * (1 + EXTRA * exp(-r / DECAY)). "
    "At RIR 0 fatigue is 2x stimulus, at RIR 2 ~1.14x.",
    "Moran-Navarro 2017: failure delayed neuromuscular recovery by ~24-48 h. "
    "With the half-life below, EXTRA=1.0 shifts recovery by ~28 h.",
    "low", heuristic=True,
)
FAILURE_FATIGUE_RIR_DECAY = _param(
    "FAILURE_FATIGUE_RIR_DECAY", 1.0, "RIR",
    "How quickly the near-failure fatigue premium disappears with RIR.",
    "Engineering choice; premium is negligible from RIR ~4.",
    "low", heuristic=True,
)
FATIGUE_HALF_LIFE_HOURS = _param(
    "FATIGUE_HALF_LIFE_HOURS", 30.0, "hours",
    "Half-life of local muscle fatigue. One value for everyone; training "
    "experience deliberately does not change it.",
    "Moran-Navarro 2017: recovery of performance within ~24-72 h after hard "
    "sessions. The exact value is an assumption.",
    "low", heuristic=True,
)
NOVELTY_MAX_MULTIPLIER = _param(
    "NOVELTY_MAX_MULTIPLIER", 1.25, "multiplier",
    "Upper bound of the extra fatigue cost of an unfamiliar exercise.",
    "Repeated bout effect (Hyldahl 2017): unaccustomed exercise causes more "
    "damage. The magnitude is not established.",
    "low", heuristic=True,
)
NOVELTY_FAMILIAR_DAYS = _param(
    "NOVELTY_FAMILIAR_DAYS", 7.0, "days",
    "An exercise done within this many days carries no novelty premium.",
    "Engineering choice.", "low", heuristic=True,
)
NOVELTY_UNFAMILIAR_DAYS = _param(
    "NOVELTY_UNFAMILIAR_DAYS", 42.0, "days",
    "At or beyond this gap (or never done) the full premium applies; the "
    "premium rises smoothly in between.",
    "Engineering choice.", "low", heuristic=True,
)

# --- Muscle contribution -----------------------------------------------------

INDIRECT_SET_CAP = _param(
    "INDIRECT_SET_CAP", 0.5, "set per set",
    "Most a secondary (indirect) muscle can receive from one set.",
    "Pelland 2024/2026: counting indirect sets as 0.5 ('fractional') fitted "
    "hypertrophy and strength data best.",
    "moderate", heuristic=False,
)
CONTRIBUTION_NORMALIZATION = _param(
    "CONTRIBUTION_NORMALIZATION", "share / max_share", "ratio",
    "Turns the catalog muscle_load_profile into per-muscle set weights: the "
    "largest share counts 1.0, others proportionally; secondary muscles are "
    "capped by INDIRECT_SET_CAP.",
    "Our normalisation of catalog data; not a research-derived coefficient.",
    "low", heuristic=True,
)
NON_TRAINING_PATTERNS = _param(
    "NON_TRAINING_PATTERNS", ("mobility",), "movement patterns",
    "Patterns that produce neither training stimulus nor fatigue in the model.",
    "Domain rule: mobility drills are not resistance training sets.",
    "n/a", heuristic=True,
)

# --- Exposure (training history) --------------------------------------------

EXPOSURE_RECENT_TAU_DAYS = _param(
    "EXPOSURE_RECENT_TAU_DAYS", 7.0, "days",
    "Time constant of the recent exposure (E7, ~weekly sets). Exponential "
    "weighting replaces hard 7/14-day windows so old sessions fade, not drop.",
    "Weekly sets per muscle is the unit used by the volume literature "
    "(Schoenfeld 2017, Pelland); the EWMA form is an engineering choice.",
    "moderate", heuristic=True,
)
EXPOSURE_LONG_TAU_DAYS = _param(
    "EXPOSURE_LONG_TAU_DAYS", 28.0, "days",
    "Time constant of the longer-term exposure (E28, average week over ~a month).",
    "Engineering choice. Used descriptively; never as an acute:chronic ratio.",
    "low", heuristic=True,
)
TREND_DEADBAND = _param(
    "TREND_DEADBAND", 0.25, "relative change",
    "Recent vs longer-term exposure must differ by more than this to report a "
    "trend (up/down).",
    "Engineering choice to avoid flapping trends.", "low", heuristic=True,
)
TREND_MIN_REFERENCE_SETS = _param(
    "TREND_MIN_REFERENCE_SETS", 1.0, "sets/week",
    "Floor of the denominator when computing the trend.",
    "Engineering choice.", "n/a", heuristic=True,
)
HISTORY_DAYS = _param(
    "HISTORY_DAYS", 90, "days",
    "How much history is loaded; ~3 x EXPOSURE_LONG_TAU_DAYS so truncation "
    "error stays small.",
    "Numerical choice.", "n/a", heuristic=True,
)
DIRECT_EXPOSURE_MIN_SETS = _param(
    "DIRECT_EXPOSURE_MIN_SETS", 1.0, "effective sets",
    "A logged exercise counts as 'having trained' a muscle (for frequency and "
    "days-since) when it gave that muscle at least this much stimulus.",
    "Engineering choice.", "n/a", heuristic=True,
)
VOLUME_ZONE_SMOOTHING_DAYS = _param(
    "VOLUME_ZONE_SMOOTHING_DAYS", 7, "days",
    "Volume zones use the mean of the last 7 end-of-day E7 values. E7 itself "
    "ripples with the training rhythm (right after vs right before a "
    "session); the mean removes that ripple so labels do not flap.",
    "Engineering choice.", "n/a", heuristic=True,
)
VOLUME_HYSTERESIS_SETS = _param(
    "VOLUME_HYSTERESIS_SETS", 0.5, "sets / week",
    "Volume zones (below / within / above target) change only when exposure "
    "crosses a bound by this margin.",
    "Engineering choice for stability.", "n/a", heuristic=True,
)
MIN_HISTORY_DAYS_FOR_UNDERLOAD = _param(
    "MIN_HISTORY_DAYS_FOR_UNDERLOAD", 14, "days",
    "A muscle is called 'underloaded' only when the user has at least this "
    "much logged history (otherwise it is 'insufficient history').",
    "Engineering choice.", "n/a", heuristic=True,
)

# --- Readiness ---------------------------------------------------------------

READINESS_FATIGUE_SCALE = _param(
    "READINESS_FATIGUE_SCALE", 8.0, "fatigue set-units",
    "Scale of readiness = exp(-local_fatigue / scale). A stabilising scale, "
    "NOT a physiological capacity. Sensitivity (6/8/10) is covered by tests.",
    "Engineering choice; with it ~8-10 hard sets read 'moderate' after 48 h "
    "and recovered after ~72 h, consistent with Moran-Navarro 2017.",
    "low", heuristic=True,
)
READINESS_LEVELS = _param(
    "READINESS_LEVELS",
    (("low", 0.0), ("moderate", 0.45), ("ready", 0.65), ("recovered", 0.85)),
    "readiness score",
    "Lower bounds of the user-facing readiness levels "
    "(Low readiness / Moderate readiness / Ready / Recovered).",
    "Engineering choice.", "n/a", heuristic=True,
)
READINESS_HYSTERESIS = _param(
    "READINESS_HYSTERESIS", 0.05, "readiness score",
    "A level changes only when the score crosses its bound by this margin.",
    "Engineering choice for stability.", "n/a", heuristic=True,
)
STATE_REPLAY_DAYS = _param(
    "STATE_REPLAY_DAYS", 14, "days",
    "Days replayed to apply hysteresis deterministically from history alone.",
    "Engineering choice.", "n/a", heuristic=True,
)
ACCUMULATED_FATIGUE_THRESHOLD = _param(
    "ACCUMULATED_FATIGUE_THRESHOLD", 0.65, "readiness score",
    "Readiness below this at the end of a day counts as a fatigued day.",
    "Engineering choice.", "n/a", heuristic=True,
)
ACCUMULATED_FATIGUE_DAYS = _param(
    "ACCUMULATED_FATIGUE_DAYS", (3, 5), "days",
    "Accumulated fatigue = fatigued on at least 3 of the last 5 days. Built "
    "from the fatigue history itself, not from a load ratio (no ACWR).",
    "Engineering choice.", "n/a", heuristic=True,
)

# --- Sleep (readiness modifier only) ----------------------------------------

SLEEP_NEED_MINUTES = _param(
    "SLEEP_NEED_MINUTES", 420, "minutes",
    "Nightly sleep below this counts as a deficit.",
    "Watson 2015 (AASM/SRS consensus): adults need >= 7 h.",
    "high", heuristic=False,
)
SLEEP_DEBT_TAU_NIGHTS = _param(
    "SLEEP_DEBT_TAU_NIGHTS", 5.0, "nights",
    "Recent nights weigh more in the sleep debt; consecutive short nights add up.",
    "Knowles 2018: consecutive nights of restriction matter more than one. "
    "Value is an assumption.",
    "low", heuristic=True,
)
SLEEP_DEBT_SCALE_MINUTES = _param(
    "SLEEP_DEBT_SCALE_MINUTES", 360.0, "minutes",
    "Saturation scale of the sleep penalty: 1 - exp(-debt / scale).",
    "Engineering choice.", "low", heuristic=True,
)
SLEEP_MAX_READINESS_PENALTY = _param(
    "SLEEP_MAX_READINESS_PENALTY", 0.15, "fraction",
    "Largest reduction of readiness from sleep debt (readiness x >= 0.85). "
    "Sleep never changes stimulus, fatigue cost or exposure.",
    "Knowles 2018; Craven 2022: sleep loss has a real but small effect on "
    "strength. Magnitude is an assumption.",
    "low", heuristic=True,
)
SLEEP_LOOKBACK_NIGHTS = _param(
    "SLEEP_LOOKBACK_NIGHTS", 14, "nights",
    "Nights considered for sleep debt (older nights weigh < 6%).",
    "Numerical choice.", "n/a", heuristic=True,
)

# --- Weekly volume targets (recommendation bands) ---------------------------

# (LOWER_TARGET, UPPER_TARGET) fractional sets per week per major muscle.
# These are bands the engine uses for prioritisation. They are not minimum
# effective or maximum recoverable volumes.
WEEKLY_SET_TARGETS: Dict[str, Dict[str, Tuple[float, float]]] = _param(
    "WEEKLY_SET_TARGETS",
    {
        "maintenance": {"beginner": (2, 6), "intermediate": (3, 6), "advanced": (4, 8)},
        "general_fitness": {"beginner": (3, 8), "intermediate": (4, 10), "advanced": (6, 12)},
        "fat_loss": {"beginner": (3, 8), "intermediate": (4, 10), "advanced": (6, 12)},
        "strength": {"beginner": (3, 8), "intermediate": (4, 10), "advanced": (6, 12)},
        "hypertrophy": {"beginner": (6, 12), "intermediate": (10, 16), "advanced": (12, 20)},
    },
    "fractional sets / week",
    "LOWER_TARGET / UPPER_TARGET bands per goal and experience used to "
    "prioritise muscles.",
    "Order of magnitude from Schoenfeld 2017, Baz-Valle 2022 (12-20 for "
    "trained men), Pelland (diminishing returns, stronger for strength), "
    "Spiering 2021 (low dose maintains), ACSM 2026 (~10 sets for hypertrophy). "
    "Exact bounds are assumptions.",
    "low", heuristic=True,
)
MAJOR_MUSCLES = _param(
    "MAJOR_MUSCLES",
    ("chest", "lats", "upper-back", "shoulders", "biceps", "triceps",
     "quads", "hamstrings", "glutes", "calves", "abs"),
    "muscle slugs",
    "Muscles with weekly targets. Others (forearms, neck, ...) are tracked for "
    "fatigue but never flagged as underloaded.",
    "Domain choice following 'all major muscle groups' guidance (ACSM 2026).",
    "n/a", heuristic=True,
)

# --- Stage 1: muscle priority & session allocation --------------------------

STAGE1_TIE_BREAK_ORDER = _param(
    "STAGE1_TIE_BREAK_ORDER",
    ("quads", "chest", "lats", "hamstrings", "shoulders", "glutes",
     "upper-back", "triceps", "biceps", "calves", "abs"),
    "muscle slugs",
    "Order used only when muscles have equal priority (e.g. a new user): large "
    "muscles first, alternating lower and upper body, so ties start with "
    "compound work instead of alphabetical order.",
    "Engineering choice.", "n/a", heuristic=True,
)

AVAILABILITY_LOW = _param(
    "AVAILABILITY_LOW", 0.50, "readiness score",
    "Below this readiness a muscle is not available for new direct work.",
    "Engineering choice.", "n/a", heuristic=True,
)
AVAILABILITY_HIGH = _param(
    "AVAILABILITY_HIGH", 0.85, "readiness score",
    "At or above this readiness a muscle is fully available; smoothstep between.",
    "Engineering choice.", "n/a", heuristic=True,
)
WEAK_POINT_BONUS = _param(
    "WEAK_POINT_BONUS", 0.5, "multiplier",
    "Priority multiplier for user weak points: x(1 + bonus). It never bypasses "
    "readiness (priority is a product with availability).",
    "Product decision.", "n/a", heuristic=True,
)
FOCUS_NEUTRAL = _param("FOCUS_NEUTRAL", 5.0, "0-10 scale", "Neutral onboarding focus.", "Onboarding default.", "n/a", True)
FOCUS_SPAN = _param("FOCUS_SPAN", 5.0, "0-10 scale", "Distance from neutral to the extremes.", "Onboarding scale.", "n/a", True)
FOCUS_MAX_ADJUSTMENT = _param(
    "FOCUS_MAX_ADJUSTMENT", 0.5, "multiplier",
    "Onboarding focus modifier = 1 + 0.5 * (focus - 5) / 5, in [0.5, 1.5]. A "
    "weak point is never reduced by a low focus.",
    "Product decision.", "n/a", heuristic=True,
)
MIN_EXPOSURES_PER_WEEK = _param(
    "MIN_EXPOSURES_PER_WEEK", 2, "sessions / week",
    "Each major muscle should be trained at least this often; drives the "
    "opportunity modifier.",
    "ACSM 2026: train all major muscle groups >= 2 days per week.",
    "moderate", heuristic=False,
)
MAX_EXPOSURES_PER_WEEK = _param(
    "MAX_EXPOSURES_PER_WEEK", 3, "sessions / week",
    "Weekly volume is split over at most this many sessions per muscle.",
    "Pelland: little hypertrophy benefit from higher frequency at equal volume.",
    "low", heuristic=True,
)
DEFAULT_WORKOUTS_PER_WEEK = _param(
    "DEFAULT_WORKOUTS_PER_WEEK", 3, "sessions / week",
    "Used when the profile does not say how often the user trains.",
    "Engineering default.", "n/a", heuristic=True,
)
OPPORTUNITY_FLOOR = _param(
    "OPPORTUNITY_FLOOR", 0.5, "multiplier",
    "Opportunity modifier = floor + (1 - floor) * smoothstep(days since trained "
    "/ target interval): recently trained muscles yield to others.",
    "Engineering choice.", "n/a", heuristic=True,
)
SESSION_SET_CAP_PER_MUSCLE = _param(
    "SESSION_SET_CAP_PER_MUSCLE", 8.0, "effective sets",
    "Most effective sets allocated to one muscle in a single session.",
    "Remmert 2025 (preprint): per-session returns diminish; the breakpoint is "
    "uncertain.",
    "low", heuristic=True,
)
MIN_SESSION_SETS = _param(
    "MIN_SESSION_SETS", 2, "sets",
    "Allocations below this are dropped instead of suggesting a single set.",
    "Engineering choice.", "n/a", heuristic=True,
)
MIN_PRIORITY = _param(
    "MIN_PRIORITY", 0.05, "priority score",
    "Muscles below this priority are not targeted this session.",
    "Engineering choice.", "n/a", heuristic=True,
)
MAX_TARGET_MUSCLES = _param(
    "MAX_TARGET_MUSCLES", 4, "muscles",
    "Most muscles Stage 1 asks Stage 2 to cover in one recommendation.",
    "Engineering choice.", "n/a", heuristic=True,
)

# --- Stage 2: exercise selection --------------------------------------------

MAX_RECOMMENDED_EXERCISES = _param(
    "MAX_RECOMMENDED_EXERCISES", 3, "exercises",
    "Number of exercises returned (matches the existing UI).",
    "UI constraint.", "n/a", heuristic=True,
)
MAX_SETS_PER_EXERCISE = _param(
    "MAX_SETS_PER_EXERCISE", 5, "sets",
    "Upper bound of prescribed sets for one exercise.",
    "Engineering choice.", "n/a", heuristic=True,
)
SELECTION_WEIGHTS = _param(
    "SELECTION_WEIGHTS",
    {"target": 1.0, "goal_fit": 0.3, "diversity": 0.15, "fatigue_conflict": 0.6, "recent_repetition": 0.1},
    "score weights",
    "Ranking weights of Stage 2: target muscle contribution + goal fit + "
    "pattern diversity - fatigue conflict - recent repetition.",
    "Ranking weights, not physiology.", "n/a", heuristic=True,
)
RECENT_REPETITION_TAU_DAYS = _param(
    "RECENT_REPETITION_TAU_DAYS", 7.0, "days",
    "Recent-repetition penalty = exp(-days since done / tau).",
    "Engineering choice.", "n/a", heuristic=True,
)
MAX_DIFFICULTY = _param(
    "MAX_DIFFICULTY", {"beginner": 3, "intermediate": 4, "advanced": 5}, "difficulty 1-5",
    "Exercise suitability filter by experience. Difficulty is never a load multiplier.",
    "Product rule.", "n/a", heuristic=True,
)
MAX_RISK = _param(
    "MAX_RISK", {"beginner": 2, "intermediate": 3, "advanced": 4}, "risk 1-5",
    "Exercise suitability filter by experience. Risk is never a load multiplier.",
    "Product rule.", "n/a", heuristic=True,
)

# Pattern families used by goal fit and diversity.
PATTERN_FAMILIES = _param(
    "PATTERN_FAMILIES",
    {
        "squat": "squat", "lunge": "squat", "hinge": "hinge",
        "push": "push", "pull": "pull", "carry": "carry",
        "core": "core", "rotation": "core", "anti-rotation": "core",
        "anti-extension": "core", "anti-lateral-flexion": "core",
        "isolation": "isolation",
        "jump": "conditioning", "locomotion": "conditioning", "full-body": "conditioning",
        "mobility": "mobility",
    },
    "pattern -> family",
    "Coarse movement families for goal fit and variety.",
    "Domain grouping.", "n/a", heuristic=True,
)
GOAL_PATTERN_FIT = _param(
    "GOAL_PATTERN_FIT",
    {
        "hypertrophy": {"isolation": 1.0, "push": 1.0, "pull": 1.0, "squat": 1.0, "hinge": 1.0,
                        "core": 0.7, "carry": 0.4, "conditioning": 0.2},
        "strength": {"squat": 1.0, "hinge": 1.0, "push": 1.0, "pull": 1.0, "carry": 0.7,
                     "isolation": 0.5, "core": 0.6, "conditioning": 0.3},
        "maintenance": {"squat": 1.0, "hinge": 1.0, "push": 1.0, "pull": 1.0, "isolation": 0.7,
                        "core": 0.8, "carry": 0.6, "conditioning": 0.4},
        "fat_loss": {"squat": 1.0, "hinge": 1.0, "push": 1.0, "pull": 1.0, "carry": 0.8,
                     "isolation": 0.5, "core": 0.7, "conditioning": 0.6},
        "general_fitness": {"squat": 1.0, "hinge": 1.0, "push": 1.0, "pull": 1.0, "carry": 0.9,
                            "conditioning": 0.8, "core": 0.9, "isolation": 0.6},
    },
    "0-1",
    "How well a movement family suits each goal (strength favours heavy "
    "compound lifts; fat loss favours compound work to preserve muscle; "
    "general fitness welcomes carries and conditioning).",
    "Informed by Currier 2023, ACSM 2026, Murphy & Koehler 2022; values are "
    "ranking weights.",
    "low", heuristic=True,
)

LOAD_TYPE_FIT = _param(
    "LOAD_TYPE_FIT",
    {
        "hypertrophy": {"external": 1.0, "machine": 1.0, "cable": 1.0, "bodyweight": 0.8, "band": 0.6, "none": 0.5},
        "strength": {"external": 1.0, "machine": 0.9, "cable": 0.8, "bodyweight": 0.6, "band": 0.4, "none": 0.4},
        "maintenance": {"external": 1.0, "machine": 1.0, "cable": 1.0, "bodyweight": 0.9, "band": 0.8, "none": 0.7},
        "fat_loss": {"external": 1.0, "machine": 1.0, "cable": 1.0, "bodyweight": 0.9, "band": 0.8, "none": 0.7},
        "general_fitness": {"external": 1.0, "machine": 1.0, "cable": 1.0, "bodyweight": 1.0, "band": 0.9, "none": 0.8},
    },
    "0-1",
    "Multiplies the pattern fit: loads that are easy to progress suit "
    "hypertrophy and strength better than bands or bodyweight variants.",
    "Progressive overload principle (ACSM 2009/2026); values are ranking weights.",
    "low", heuristic=True,
)

# --- Prescription policy (goal-specific, shared physiology) -----------------

# Target RIR ranges (low, high) by goal; compound vs isolation where it matters.
TARGET_RIR = _param(
    "TARGET_RIR",
    {
        "hypertrophy": {"compound": (1, 3), "isolation": (0, 2)},
        "strength": {"compound": (1, 3), "isolation": (1, 3)},
        "maintenance": {"compound": (1, 3), "isolation": (1, 3)},
        "fat_loss": {"compound": (1, 3), "isolation": (1, 3)},
        "general_fitness": {"compound": (2, 4), "isolation": (2, 4)},
    },
    "RIR",
    "Effort to prescribe. Close-to-failure without failure as default.",
    "ACSM 2026: 1-2 RIR gives gains similar to failure; Robinson 2024: strength "
    "gains depend little on RIR; Moran-Navarro 2017: failure costs recovery.",
    "moderate", heuristic=True,
)
BEGINNER_EXTRA_RIR = _param(
    "BEGINNER_EXTRA_RIR", 1, "RIR",
    "Beginners are prescribed one more rep in reserve (technique, rating error).",
    "Product rule informed by Halperin 2022 (rating error).",
    "low", heuristic=True,
)
STRENGTH_REP_RANGE = _param(
    "STRENGTH_REP_RANGE", (3, 6), "reps",
    "Rep range prescribed for loaded compound lifts when the goal is strength.",
    "Lopez 2021; Currier 2023: heavier loads (~>80% 1RM) favour strength.",
    "moderate", heuristic=False,
)
HEAVY_SET_MAX_REPS_TO_FAILURE = _param(
    "HEAVY_SET_MAX_REPS_TO_FAILURE", 6, "reps + RIR",
    "A set counts as 'heavy' (strength-relevant) when reps + RIR <= this (~6RM).",
    "Lopez 2021 / ACSM 2009: heavy loading ~1-6 RM.",
    "moderate", heuristic=False,
)

# --- Performance trend -------------------------------------------------------

E1RM_MAX_REPS = _param(
    "E1RM_MAX_REPS", 12, "reps + RIR",
    "Estimated 1RM (Epley) is only computed for sets with reps + RIR <= this; "
    "prediction error grows with reps.",
    "Common practice; formula error increases at high reps.",
    "moderate", heuristic=True,
)
PROGRESSION_WEEKS = _param("PROGRESSION_WEEKS", 6, "weeks", "Window of the e1RM trend.", "Engineering choice.", "n/a", True)
PROGRESSION_THRESHOLDS = _param(
    "PROGRESSION_THRESHOLDS", {"progress": 0.025, "regression": -0.025}, "relative change",
    "e1RM change between the earlier and later half of the window that counts "
    "as progress / regression; otherwise plateau.",
    "Engineering choice (~1 rep of rating error is ~2.5-3% e1RM).",
    "low", heuristic=True,
)

# --- Session training stress proxy (dashboard/heatmap tree only) ------------

HEATMAP_FULL_SCALE_RATIO = _param(
    "HEATMAP_FULL_SCALE_RATIO", 1.5, "x typical session",
    "Heatmap intensity_percent = 100 * min(1, day stress / typical / ratio): a "
    "typical session reads ~67%, 1.5x typical or more reads 100%. Relative "
    "intensity of the day for display; not a physiological load percentage "
    "and never used for decisions.",
    "Engineering choice.", "n/a", heuristic=True,
)
HEATMAP_PRIOR_TYPICAL_STRESS = _param(
    "HEATMAP_PRIOR_TYPICAL_STRESS", 14.0, "stress proxy units",
    "Prior 'typical session' of the heatmap for users without history: "
    "roughly a normal ~10 hard-set session done with new exercises (novelty "
    "raises a new user's stress proxy), so such a session reads ~67%. "
    "Display only; the recovery notes keep STRESS_MIN_TYPICAL_SETS.",
    "Engineering choice.", "n/a", heuristic=True,
)
HEATMAP_PRIOR_SESSIONS = _param(
    "HEATMAP_PRIOR_SESSIONS", 2, "sessions",
    "Weight of the prior in the heatmap baseline: (k * median + w * prior) / "
    "(k + w). It fades as the user's own training days accumulate.",
    "Engineering choice (shrinkage toward a prior).", "n/a", heuristic=True,
)
STRESS_BASELINE_DAYS = _param(
    "STRESS_BASELINE_DAYS", 56, "days",
    "The 'typical session' is the median stress proxy of training days in "
    "this many preceding days.",
    "Engineering choice.", "n/a", heuristic=True,
)
STRESS_MIN_TYPICAL_SETS = _param(
    "STRESS_MIN_TYPICAL_SETS", 10.0, "hard sets",
    "Floor for the 'typical session' so new users are not compared to a tiny "
    "baseline.",
    "Engineering choice.", "n/a", heuristic=True,
)
HIGH_DAY_STRESS_RATIOS = _param(
    "HIGH_DAY_STRESS_RATIOS", {"high": 1.5, "very_high": 2.0}, "x typical session",
    "A day well above the user's typical session triggers a recovery note.",
    "Engineering choice.", "n/a", heuristic=True,
)

# --- Recovery snapshot -------------------------------------------------------

TRAINING_READINESS_LOOKBACK_DAYS = _param(
    "TRAINING_READINESS_LOOKBACK_DAYS", 7, "days",
    "Muscles trained within this window feed the recovery snapshot's training "
    "readiness score.",
    "Engineering choice.", "n/a", heuristic=True,
)

# --- Input sanitising and display ----------------------------------------

MAX_WORKOUTS_PER_WEEK_INPUT = _param(
    "MAX_WORKOUTS_PER_WEEK_INPUT", 14, "sessions / week",
    "Upper clamp of the profile's workouts_per_week.", "Input validation.", "n/a", True,
)
GOAL_FIT_DEFAULT = _param(
    "GOAL_FIT_DEFAULT", 0.5, "0-1",
    "Goal fit of a movement family missing from GOAL_PATTERN_FIT.",
    "Neutral ranking default.", "n/a", True,
)
SUMMARY_WINDOW_DAYS = _param(
    "SUMMARY_WINDOW_DAYS", 7, "days",
    "Window of the descriptive weekly summaries (sessions, hard sets, average RPE).",
    "Reporting window.", "n/a", True,
)
FREQUENCY_WINDOW_DAYS = _param(
    "FREQUENCY_WINDOW_DAYS", 28, "days",
    "Window of the descriptive frequency and exercise-variety summaries.",
    "Reporting window.", "n/a", True,
)
DISPLAY_MIN_SETS = _param(
    "DISPLAY_MIN_SETS", 0.05, "sets / week",
    "Muscles or patterns below this exposure are omitted from summaries.",
    "Display rounding.", "n/a", True,
)

MODEL_VERSION = 2
