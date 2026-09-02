CHRONIC_WINDOW_DAYS = 14

REFERENCE_CAPACITY_WEIGHT = 0.3
REFERENCE_HISTORY_WEIGHT = 0.7

MAX_DURATION_BONUS = 0.2

BODYWEIGHT_FACTOR = 0.65

GLOBAL_LOAD_SCALE = 1.0

REPETITION_EXPONENT = 0.85
REPETITION_SCALE = 1.0

TIME_BASE_SECONDS = 30.0
TIME_EXPONENT = 0.85
TIME_SCALE = 1.0

MOVEMENT_FACTORS = {
    "push": 1.00,
    "pull": 1.05,
    "lower": 1.05,
    "core": 0.80,
    "mobility": 0.40,
    "full_body": 1.10,
    "accessory": 0.75,
}

BODYWEIGHT_RATIOS = {
    "push-ups": 0.64,
    "pushup": 0.64,
    "bench-push-ups": 0.55,
    "bench-dips": 0.70,
    "dips": 0.87,
    "pull-ups": 1.00,
    "plank": 0.45,
    "side-plank": 0.35,
    "wall-sit": 0.55,
    "burpee": 1.10,
    "jump-squat": 1.15,
    "jumping-jacks": 0.75,
    "mountain-climbers": 0.65,
    "bear-crawl": 0.65,
    "lunge-bodyweight": 0.85,
    "lunges": 0.85,
    "squat-bodyweight": 0.90,
    "squats": 0.90,
    "dead-bug": 0.45,
    "bicycle": 0.45,
    "bird-dog": 0.35,
    "glute-bridge": 0.70,
    "kickback": 0.45,
}

BODYWEIGHT_RATIO = BODYWEIGHT_RATIOS

TIME_BASED_EXERCISES = {
    "plank",
    "side-plank",
    "wall-sit",
    "dead-hang",
    "hollow-hold",
    "glute-bridge-hold",
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
