import math
from dataclasses import dataclass
from datetime import date, datetime
from myapp.app.models.training_session import TrainingSession
from myapp.app.training_engine.models.exercise import Exercise
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
    # basic clamp
    @staticmethod
    def clamp(v, mn, mx):
        return max(mn, min(v, mx))

    # reps parser (simple)
    @staticmethod
    def parse_reps(v):
        if v is None:
            return 0
        if isinstance(v, int):
            return v
        t = str(v)
        if "-" in t:
            try:
                a, b = t.split("-")
                return (int(a) + int(b)) / 2
            except:
                return 0
        try:
            return float(t)
        except:
            return 0

    # BMI (WHO standard)
    @staticmethod
    def bmi(w, h):
        if not w or not h:
            return 22.0
        return w / ((h / 100) ** 2)

    # body fat (Deurenberg et al.)
    @staticmethod
    def body_fat(w, h, age, sex):
        bmi = TrainingLoadService.bmi(w, h)
        if sex == "male":
            bf = 1.20 * bmi + 0.23 * age - 16.2
        else:
            bf = 1.20 * bmi + 0.23 * age - 5.4
        return TrainingLoadService.clamp(bf, 4, 50)

    # FFMI (Kouri et al.)
    @staticmethod
    def ffmi(w, h, age, sex):
        bf = TrainingLoadService.body_fat(w, h, age, sex)
        lean = w * (1 - bf / 100)
        hh = h / 100
        ffmi = lean / (hh * hh)
        ffmi += 6.1 * (1.8 - hh)
        return ffmi

    # BMR (Mifflin-St Jeor)
    @staticmethod
    def bmr(w, h, age, sex):
        if sex == "female":
            return 10 * w + 6.25 * h - 5 * age - 161
        return 10 * w + 6.25 * h - 5 * age + 5

    # simple endurance strength index
    @staticmethod
    def estimated_strength(push, squat, sit):
        p = min(push / 60, 1.0)
        s = min(squat / 80, 1.0)
        si = min(sit / 80, 1.0)
        return p * 0.40 + s * 0.35 + si * 0.25

    # 1RM estimate (Epley/Brzycki)
    @staticmethod
    def estimate_1rm(w, reps):
        if w <= 0:
            return 0
        reps = max(1, reps)
        if reps <= 10:
            return w * (1 + reps / 30.0)
        return w * 36.0 / (37.0 - reps)

    # relative intensity (%1RM concept)
    @staticmethod
    def relative_intensity(load, rm):
        if rm <= 0:
            return 0.55
        return TrainingLoadService.clamp(load / rm, 0.0, 1.25)

    # build user capacity (simple multiplicative model)
    @staticmethod
    def build_capacity(user):
        age = user.age or 25
        sex = (user.sex or "male").lower()
        w = user.weight or 70
        h = user.height or 175

        bmi = TrainingLoadService.bmi(w, h)
        ffmi = TrainingLoadService.ffmi(w, h, age, sex)
        bmr = TrainingLoadService.bmr(w, h, age, sex)

        perf = user.performance_states.order_by(
            PerformanceState.created_at.desc()
        ).first()
        push = getattr(perf, "pushups", 0) if perf else 0
        squat = getattr(perf, "squats", 0) if perf else 0
        sit = getattr(perf, "situps", 0) if perf else 0

        strength_index = TrainingLoadService.estimated_strength(push, squat, sit)

        # age factor (basic decline curve)
        if age < 18:
            age_f = 0.90
        elif age <= 35:
            age_f = 1.00
        elif age <= 50:
            age_f = 0.95
        elif age <= 65:
            age_f = 0.88
        else:
            age_f = 0.80

        # bmi factor (optimal range 18.5–25)
        if bmi < 18.5:
            bmi_f = 0.92
        elif bmi <= 25:
            bmi_f = 1.00
        elif bmi <= 30:
            bmi_f = 0.98
        else:
            bmi_f = 0.95

        # ffmi factor (higher ffmi → more capacity)
        ffmi_f = TrainingLoadService.clamp(ffmi / 20.0, 0.80, 1.30)

        # strength factor
        if strength_index < 0.20:
            str_f = 0.80
        elif strength_index < 0.40:
            str_f = 0.90
        elif strength_index < 0.60:
            str_f = 1.00
        elif strength_index < 0.80:
            str_f = 1.10
        else:
            str_f = 1.20

        # experience
        exp = (user.experience or "beginner").lower()
        exp_f = {
            "beginner": 0.90,
            "novice": 0.95,
            "intermediate": 1.00,
            "advanced": 1.10,
            "elite": 1.20,
        }.get(exp, 1.00)

        # activity
        act = (user.activity or "moderate").lower()
        act_f = {
            "sedentary": 0.90,
            "low": 0.95,
            "moderate": 1.00,
            "high": 1.05,
            "very_high": 1.10,
        }.get(act, 1.00)

        # goal
        goal = (user.goal or "maintenance").lower()
        goal_f = {
            "fat_loss": 1.05,
            "maintenance": 1.00,
            "muscle_gain": 1.08,
            "strength": 1.12,
            "performance": 1.15,
        }.get(goal, 1.00)

        # frequency
        freq = user.workouts_per_week or 3
        if freq <= 2:
            freq_f = 0.95
        elif freq <= 4:
            freq_f = 1.00
        elif freq <= 6:
            freq_f = 1.05
        else:
            freq_f = 1.10

        capacity = age_f * bmi_f * ffmi_f * str_f * exp_f * act_f * goal_f * freq_f

        return UserCapacity(
            age=age,
            sex=sex,
            weight=w,
            height=h,
            bmi=bmi,
            ffmi=ffmi,
            bmr=bmr,
            strength_index=strength_index,
            capacity=capacity,
        )

    # volume load (classic training science)
    @staticmethod
    def exercise_volume(sets, reps, load):
        if load <= 0:
            load = 0.4
        return sets * reps * load

    # intensity factor (%1RM zones)
    @staticmethod
    def intensity_factor(load, rm):
        ri = TrainingLoadService.relative_intensity(load, rm)
        if ri < 0.50:
            return 0.75
        if ri < 0.60:
            return 0.90
        if ri < 0.70:
            return 1.00
        if ri < 0.80:
            return 1.15
        if ri < 0.90:
            return 1.35
        return 1.55

    # movement pattern cost (basic EMG/biomech logic)
    @staticmethod
    def movement_factor(ex):
        mp = (ex.movement_pattern or "").lower()
        vals = {
            "upper-body": 1.00,
            "lower-body": 1.20,
            "core": 0.85,
            "full-body": 1.35,
            "mobility": 0.45,
        }
        return vals.get(mp, 1.00)

    # difficulty factor (skill complexity)
    @staticmethod
    def difficulty_factor(ex):
        return 1.0 + ((ex.difficulty or 1) - 1) * 0.12

    # risk factor (injury risk multiplier)
    @staticmethod
    def risk_factor(ex):
        return 1.0 + (ex.risk_level or 1) * 0.05

    # sRPE (Foster et al.)
    @staticmethod
    def rpe_factor(rpe):
        if rpe is None:
            return 1.0
        return {
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
        }.get(int(rpe), 1.0)

    # main load calc
    @staticmethod
    def compute_exercise_load(se, ex: Exercise, cap: UserCapacity):
        sets = se.sets_done or se.sets_planned or 0
        reps = TrainingLoadService.parse_reps(se.reps_done or se.reps_planned)
        load = se.load_done or se.load_planned or 0
        rpe = se.rpe or 7

        rm = TrainingLoadService.estimate_1rm(load, reps)
        vol = TrainingLoadService.exercise_volume(sets, reps, max(load, 0.4))
        inten = TrainingLoadService.intensity_factor(load, rm)
        move = TrainingLoadService.movement_factor(ex)
        diff = TrainingLoadService.difficulty_factor(ex)
        risk = TrainingLoadService.risk_factor(ex)
        rpe_f = TrainingLoadService.rpe_factor(rpe)

        external = vol * inten * move * diff * risk
        internal = external * rpe_f * cap.capacity

        return {
            "sets": sets,
            "reps": reps,
            "load": load,
            "estimated_1rm": rm,
            "volume": vol,
            "external_load": external,
            "internal_load": internal,
        }

    # muscle load distribution (simple EMG-like split)
    @staticmethod
    def compute_muscle_load(ex: Exercise, load, muscles):
        prof = ex.muscle_load_profile or {}
        if prof:
            for m, pct in prof.items():
                muscles[m] = muscles.get(m, 0) + load * pct
            return

        primary = ex.muscles_primary or []
        secondary = ex.muscles_secondary or []

        if primary:
            v = load * 0.70 / len(primary)
            for m in primary:
                muscles[m] = muscles.get(m, 0) + v

        if secondary:
            v = load * 0.30 / len(secondary)
            for m in secondary:
                muscles[m] = muscles.get(m, 0) + v

    # CNS stress (basic workload model)
    @staticmethod
    def compute_cns_stress(total):
        if total < 150:
            return 10
        if total < 300:
            return 20
        if total < 500:
            return 35
        if total < 700:
            return 50
        if total < 900:
            return 65
        if total < 1200:
            return 80
        return 95

    # recovery hours (simple load - hours curve)
    @staticmethod
    def compute_recovery_hours(load):
        if load < 150:
            return 12
        if load < 300:
            return 18
        if load < 500:
            return 24
        if load < 700:
            return 36
        if load < 900:
            return 48
        if load < 1200:
            return 60
        return 72

    @staticmethod
    def get_daily_load(user_id: int) -> int:
        today = date.today()
        start = datetime.combine(today, datetime.min.time())
        end = datetime.combine(today, datetime.max.time())

        sessions = TrainingSession.query.filter(
            TrainingSession.user_id == user_id,
            TrainingSession.started_at >= start,
            TrainingSession.started_at <= end,
        ).all()

        return sum(s.internal_load or 0 for s in sessions)
