from dataclasses import dataclass
from myapp.app.training_engine.models.performance_state import PerformanceState


@dataclass
class UserCapacity:
    age: int
    sex: str
    weight: float
    height: float
    bmi: float
    ffmi: float
    bmr: float
    strength_index: float
    capacity: float


class TrainingLoadService:

    # BASIC HELPERS

    @staticmethod
    def clamp(value, minimum, maximum):
        return max(minimum, min(value, maximum))

    @staticmethod
    def parse_reps(value):
        if value is None:
            return 0.0

        if isinstance(value, (int, float)):
            return max(float(value), 0.0)

        text = str(value).strip()

        if not text:
            return 0.0

        text = text.replace("–", "-").replace("—", "-").replace("/", "-")

        if "-" in text:
            parts = text.split("-", 1)

            try:
                first = float(parts[0].strip())
                second = float(parts[1].strip())

                return max((first + second) / 2.0, 0.0)
            except (ValueError, TypeError):
                return 0.0

        try:
            return max(float(text.split()[0]), 0.0)
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def parse_float(value):
        if value is None:
            return 0.0

        if isinstance(value, (int, float)):
            return max(float(value), 0.0)

        try:
            return max(float(str(value).strip()), 0.0)
        except (ValueError, TypeError):
            return 0.0

    # USER CAPACITY

    @staticmethod
    def bmi(weight, height):
        if not weight or not height:
            return 22.0

        height_m = height / 100.0

        if height_m <= 0:
            return 22.0

        return weight / (height_m**2)

    @staticmethod
    def body_fat(weight, height, age, sex):
        bmi = TrainingLoadService.bmi(weight, height)

        if sex == "female":
            value = 1.20 * bmi + 0.23 * age - 5.4
        else:
            value = 1.20 * bmi + 0.23 * age - 16.2

        return TrainingLoadService.clamp(
            value,
            4.0,
            50.0,
        )

    @staticmethod
    def ffmi(weight, height, age, sex):
        if not height:
            return 18.0

        body_fat = TrainingLoadService.body_fat(
            weight,
            height,
            age,
            sex,
        )

        lean_mass = weight * (1.0 - body_fat / 100.0)
        height_m = height / 100.0

        if height_m <= 0:
            return 18.0

        value = lean_mass / (height_m**2)
        value += 6.1 * (1.8 - height_m)

        return value

    @staticmethod
    def bmr(weight, height, age, sex):
        if sex == "female":
            return 10 * weight + 6.25 * height - 5 * age - 161

        return 10 * weight + 6.25 * height - 5 * age + 5

    @staticmethod
    def estimated_strength(pushups, squats, situps):
        push_factor = min(pushups / 60.0, 1.0)
        squat_factor = min(squats / 80.0, 1.0)
        situp_factor = min(situps / 80.0, 1.0)

        return push_factor * 0.40 + squat_factor * 0.35 + situp_factor * 0.25

    @staticmethod
    def build_capacity(user):
        age = getattr(user, "age", None) or 25
        sex = (getattr(user, "sex", None) or "male").lower()

        weight = getattr(user, "weight", None) or 70.0
        height = getattr(user, "height", None) or 175.0

        bmi = TrainingLoadService.bmi(
            weight,
            height,
        )

        ffmi = TrainingLoadService.ffmi(
            weight,
            height,
            age,
            sex,
        )

        bmr = TrainingLoadService.bmr(
            weight,
            height,
            age,
            sex,
        )

        perf = user.performance_states.order_by(
            PerformanceState.created_at.desc()
        ).first()

        pushups = getattr(perf, "pushups", 0) or 0
        squats = getattr(perf, "squats", 0) or 0
        situps = getattr(perf, "situps", 0) or 0

        strength_index = TrainingLoadService.estimated_strength(
            pushups,
            squats,
            situps,
        )

        # Age
        if age < 18:
            age_factor = 0.90
        elif age <= 35:
            age_factor = 1.00
        elif age <= 50:
            age_factor = 0.95
        elif age <= 65:
            age_factor = 0.88
        else:
            age_factor = 0.80

        # BMI
        if bmi < 18.5:
            bmi_factor = 0.92
        elif bmi <= 25:
            bmi_factor = 1.00
        elif bmi <= 30:
            bmi_factor = 0.98
        else:
            bmi_factor = 0.95

        # FFMI
        ffmi_factor = TrainingLoadService.clamp(
            ffmi / 20.0,
            0.80,
            1.30,
        )

        # Strength
        if strength_index < 0.20:
            strength_factor = 0.80
        elif strength_index < 0.40:
            strength_factor = 0.90
        elif strength_index < 0.60:
            strength_factor = 1.00
        elif strength_index < 0.80:
            strength_factor = 1.10
        else:
            strength_factor = 1.20

        # Experience
        experience = (getattr(user, "experience", None) or "beginner").lower()

        experience_factor = {
            "beginner": 0.90,
            "novice": 0.95,
            "intermediate": 1.00,
            "advanced": 1.10,
            "elite": 1.20,
        }.get(experience, 1.00)

        # Activity
        activity = (getattr(user, "activity", None) or "moderate").lower()

        activity_factor = {
            "sedentary": 0.90,
            "low": 0.95,
            "moderate": 1.00,
            "high": 1.05,
            "very_high": 1.10,
        }.get(activity, 1.00)

        # Goal
        goal = (getattr(user, "goal", None) or "maintenance").lower()

        goal_factor = {
            "fat_loss": 1.05,
            "maintenance": 1.00,
            "muscle_gain": 1.08,
            "strength": 1.12,
            "performance": 1.15,
        }.get(goal, 1.00)

        # Training frequency
        frequency = getattr(user, "workouts_per_week", None) or 3

        if frequency <= 2:
            frequency_factor = 0.95
        elif frequency <= 4:
            frequency_factor = 1.00
        elif frequency <= 6:
            frequency_factor = 1.05
        else:
            frequency_factor = 1.10

        capacity = (
            age_factor
            * bmi_factor
            * ffmi_factor
            * strength_factor
            * experience_factor
            * activity_factor
            * goal_factor
            * frequency_factor
        )

        return UserCapacity(
            age=age,
            sex=sex,
            weight=float(weight),
            height=float(height),
            bmi=float(bmi),
            ffmi=float(ffmi),
            bmr=float(bmr),
            strength_index=float(strength_index),
            capacity=float(capacity),
        )

    # EXERCISE LOAD

    @staticmethod
    def estimate_1rm(weight, reps):
        if weight <= 0:
            return 0.0

        reps = max(int(reps), 1)

        if reps <= 10:
            return weight * (1.0 + reps / 30.0)

        if reps >= 37:
            return weight

        return weight * 36.0 / (37.0 - reps)

    @staticmethod
    def relative_intensity(load, one_rm):
        if one_rm <= 0:
            return 0.55

        return TrainingLoadService.clamp(
            load / one_rm,
            0.0,
            1.25,
        )

    @staticmethod
    def intensity_factor(load, one_rm):
        relative = TrainingLoadService.relative_intensity(
            load,
            one_rm,
        )

        if relative < 0.50:
            return 0.75

        if relative < 0.60:
            return 0.90

        if relative < 0.70:
            return 1.00

        if relative < 0.80:
            return 1.15

        if relative < 0.90:
            return 1.35

        return 1.55

    @staticmethod
    def exercise_volume(sets, reps, load):
        if sets <= 0 or reps <= 0:
            return 0.0

        effective_load = load if load > 0 else 0.4

        return sets * reps * effective_load

    # EXERCISE FACTORS

    @staticmethod
    def movement_factor(exercise):
        pattern = (getattr(exercise, "movement_pattern", None) or "").lower()

        values = {
            "upper-body": 1.00,
            "lower-body": 1.20,
            "core": 0.85,
            "full-body": 1.35,
            "mobility": 0.45,
        }

        if pattern in values:
            return values[pattern]

        if "push" in pattern:
            return 1.05

        if "pull" in pattern:
            return 1.10

        if "hinge" in pattern:
            return 1.20

        if "squat" in pattern:
            return 1.15

        return 1.00

    @staticmethod
    def difficulty_factor(exercise):
        difficulty = TrainingLoadService.parse_float(getattr(exercise, "difficulty", 1))

        difficulty = TrainingLoadService.clamp(
            difficulty,
            1.0,
            5.0,
        )

        return 0.90 + difficulty * 0.10

    @staticmethod
    def risk_factor(exercise):
        risk = TrainingLoadService.parse_float(getattr(exercise, "risk_level", 1))

        risk = TrainingLoadService.clamp(
            risk,
            0.0,
            5.0,
        )

        return 1.0 + risk * 0.05

    @staticmethod
    def rpe_factor(rpe):
        if rpe is None:
            return 1.0

        try:
            value = int(round(float(rpe)))
        except (ValueError, TypeError):
            return 1.0

        values = {
            1: 0.55,
            2: 0.60,
            3: 0.68,
            4: 0.75,
            5: 0.85,
            6: 0.95,
            7: 1.05,
            8: 1.15,
            9: 1.28,
            10: 1.40,
        }

        return values.get(
            TrainingLoadService.clamp(value, 1, 10),
            1.0,
        )

    # MAIN EXERCISE CALCULATION

    @staticmethod
    def compute_exercise_load(
        session_exercise,
        exercise,
        capacity,
    ):
        sets = (
            session_exercise.sets_done
            if session_exercise.sets_done is not None
            else session_exercise.sets_planned or 0
        )

        reps = TrainingLoadService.parse_reps(
            session_exercise.reps_done
            if session_exercise.reps_done is not None
            else session_exercise.reps_planned
        )

        load = (
            session_exercise.load_done
            if session_exercise.load_done is not None
            else session_exercise.load_planned or 0
        )

        sets = max(int(sets), 0)
        reps = max(float(reps), 0.0)
        load = max(float(load or 0), 0.0)

        rpe = session_exercise.rpe if session_exercise.rpe is not None else 7

        # Bodyweight exercises
        if load <= 0:
            user_weight = capacity.weight

            equipment = (
                getattr(
                    exercise,
                    "equipment",
                    None,
                )
                or []
            )

            if isinstance(equipment, str):
                equipment = [equipment]

            normalized_equipment = {
                str(item).lower().replace(" ", "") for item in equipment
            }

            slug = (getattr(exercise, "slug", None) or "").lower()

            bodyweight_ratios = {
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

            if "bodyweight" in normalized_equipment:
                ratio = bodyweight_ratios.get(
                    slug,
                    0.50,
                )

                effective_load = user_weight * ratio
            else:
                effective_load = user_weight * 0.50

        else:
            effective_load = load

        one_rm = TrainingLoadService.estimate_1rm(
            effective_load,
            reps,
        )

        volume = TrainingLoadService.exercise_volume(
            sets,
            reps,
            effective_load,
        )

        intensity = TrainingLoadService.intensity_factor(
            effective_load,
            one_rm,
        )

        movement = TrainingLoadService.movement_factor(
            exercise,
        )

        difficulty = TrainingLoadService.difficulty_factor(
            exercise,
        )

        risk = TrainingLoadService.risk_factor(
            exercise,
        )

        rpe_multiplier = TrainingLoadService.rpe_factor(
            rpe,
        )

        external_load = volume * intensity * movement * difficulty * risk

        internal_load = external_load * rpe_multiplier * capacity.capacity

        return {
            "sets": sets,
            "reps": reps,
            "load": effective_load,
            "estimated_1rm": one_rm,
            "volume": volume,
            "external_load": external_load,
            "internal_load": internal_load,
        }

    # MUSCLE LOAD

    @staticmethod
    def compute_muscle_load(
        exercise,
        internal_load,
        muscles,
    ):
        profile = getattr(exercise, "muscle_load_profile", None) or {}

        if profile:
            for muscle, percentage in profile.items():
                try:
                    factor = float(percentage)
                except (ValueError, TypeError):
                    continue

                if factor <= 0:
                    continue

                muscles[muscle] = muscles.get(muscle, 0.0) + internal_load * factor

            return

        primary = getattr(exercise, "muscles_primary", None) or []

        secondary = getattr(exercise, "muscles_secondary", None) or []

        if primary:
            primary_load = internal_load * 0.70 / len(primary)

            for muscle in primary:
                muscles[muscle] = muscles.get(muscle, 0.0) + primary_load

        if secondary:
            secondary_load = internal_load * 0.30 / len(secondary)

            for muscle in secondary:
                muscles[muscle] = muscles.get(muscle, 0.0) + secondary_load

    # RECOVERY HELPERS

    @staticmethod
    def compute_cns_stress(total_load):
        if total_load < 150:
            return 10

        if total_load < 300:
            return 20

        if total_load < 500:
            return 35

        if total_load < 700:
            return 50

        if total_load < 900:
            return 65

        if total_load < 1200:
            return 80

        return 95

    @staticmethod
    def compute_recovery_hours(total_load):
        if total_load < 150:
            return 12

        if total_load < 300:
            return 18

        if total_load < 500:
            return 24

        if total_load < 700:
            return 36

        if total_load < 900:
            return 48

        if total_load < 1200:
            return 60

        return 72
