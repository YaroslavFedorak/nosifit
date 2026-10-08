CHRONIC_WINDOW_DAYS = 14

REFERENCE_CAPACITY_WEIGHT = 0.3
REFERENCE_HISTORY_WEIGHT = 0.7

MAX_DURATION_BONUS = 0.2

GLOBAL_LOAD_SCALE = 1.0

# Fallback for bodyweight exercises that predate catalog bodyweight_ratio.
DEFAULT_BODYWEIGHT_RATIO = 0.50

# Duration load metric: sets x (seconds / TIME_BASE_SECONDS) ** TIME_EXPONENT.
# It scales hold time into internal load units for duration exercises only;
# it is not a repetition count and never changes an exercise prescription.
TIME_BASE_SECONDS = 30.0
TIME_EXPONENT = 0.85
TIME_SCALE = 1.0

MOVEMENT_FACTORS = {
    "squat": 1.08,
    "hinge": 1.08,
    "lunge": 1.05,
    "push": 1.00,
    "pull": 1.05,
    "carry": 1.05,
    "rotation": 0.90,
    "anti-rotation": 0.90,
    "anti-extension": 0.90,
    "anti-lateral-flexion": 0.90,
    "core": 0.90,
    "isolation": 0.80,
    "locomotion": 1.05,
    "jump": 1.10,
    "full-body": 1.15,
    "mobility": 0.30,
    # Patterns used by the catalog before the measurement-type redesign.
    "upper-body": 1.00,
    "lower-body": 1.10,
    "accessory": 0.80,
}

MIN_REFERENCE_LOAD = {
    "beginner": 70.0,
    "intermediate": 90.0,
    "advanced": 110.0,
    "elite": 120.0,
}

MIN_REFERENCE_BY_LEVEL = {
    "початківець": 70.0,
    "середній": 90.0,
    "досвідчений": 110.0,
    "просунутий": 110.0,
    "елітний": 120.0,
}

