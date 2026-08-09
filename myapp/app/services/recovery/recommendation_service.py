import json
import os
from typing import List, Dict

from myapp.app.models.recovery.habit import RecoveryHabit
from myapp.app.services.recovery.constants import RecoveryTrigger
from myapp.app.services.recovery.constants import (
    TRAINING_LOAD_HEAVY,
)

HABITS_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "recovery_engine",
    "data",
    "habits",
    "habits.json",
)

SHORT_TEXTS = {
    "sleep_8h": "Спати 8 годин",
    "consistent_sleep": "Лягай в один час",
    "screen_off_before_sleep": "Без екранів перед сном",
    "drink_water": "Випий воду",
    "electrolytes": "Електроліти після навантаження",
    "balanced_meal": "Збалансований прийом їжі",
    "post_workout_protein": "Протеїн після тренування",
    "post_workout_carbs": "Вуглеводи після тренування",
    "walk_30m": "Прогулянка 30 хв",
    "stretching": "Розтяжка",
    "mobility": "Мобільність",
    "foam_roll": "Фоам рол",
    "breathing_reset": "Дихальна пауза",
    "meditation": "Медитація",
    "journal_stress": "Записати стрес",
    "full_rest_day": "День відпочинку",
    "deload_week": "Тиждень розвантаження",
    "massage_or_physio": "Масаж або фізіо",
}

ICON_MAP = {
    "sleep": "sleep",
    "sleep_deficit": "sleep",
    "weak": "sleep",
    "hydration": "hydration",
    "hydration_low": "hydration",
    "recovery": "recovery",
    "rest": "recovery",
    "recommended": "recovery",
    "activity": "activity",
    "after_training": "activity",
    "balance": "activity",
    "stress": "stress",
    "low_energy": "stress",
    "nutrition": "nutrition",
    "habit_missing": "nutrition",
    "massage": "massage",
    "massage_needed": "massage",
    "hand_heart": "massage",
}


class RecommendationService:
    def __init__(self):
        with open(HABITS_PATH, "r", encoding="utf-8") as f:
            self.habits = json.load(f)

    def detect_triggers(
        self,
        sleep_score: int,
        recovery_score: int,
        energy_score: int,
        habit_score: int,
        daily_load: float,
    ) -> List[str]:

        triggers = []

        if sleep_score < 70:
            triggers.append(RecoveryTrigger.SLEEP_DEFICIT.value)

        if recovery_score < 40:
            triggers.append(RecoveryTrigger.LOW_RECOVERY.value)

        if energy_score < 60:
            triggers.append(RecoveryTrigger.LOW_ENERGY.value)

        if habit_score < 50:
            triggers.append(RecoveryTrigger.RECOVERY.value)

        if daily_load > TRAINING_LOAD_HEAVY:
            triggers.append(RecoveryTrigger.AFTER_TRAINING.value)

        return triggers

    def filter_habits_by_triggers(self, triggers: List[str]) -> List[Dict]:
        matched = []
        for habit in self.habits:
            if any(t in habit.get("recommended_when", []) for t in triggers):
                matched.append(habit)
        return matched

    def sort_habits(self, habits: List[Dict]) -> List[Dict]:
        category_order = {
            "hydration": 0,
            "sleep": 1,
            "nutrition": 2,
            "activity": 3,
            "stress": 4,
            "recovery": 5,
        }
        return sorted(
            habits,
            key=lambda h: (
                -h["points"],
                category_order.get(h["category"], 99),
                h["slug"],
            ),
        )

    def build_recommendations(
        self,
        sleep_score: int,
        recovery_score: int,
        energy_score: int,
        habit_score: int,
        daily_load: float,
    ) -> List[Dict]:

        triggers = self.detect_triggers(
            sleep_score,
            recovery_score,
            energy_score,
            habit_score,
            daily_load,
        )

        habits = self.sort_habits(self.filter_habits_by_triggers(triggers))

        recs = []

        for h in habits[:5]:
            db_habit = RecoveryHabit.query.filter_by(slug=h["slug"]).first()
            if not db_habit:
                continue

            mapped_icon = ICON_MAP.get(db_habit.icon, "recovery")
            short_text = SHORT_TEXTS.get(db_habit.slug, h["name"])

            recs.append(
                {
                    "habit_id": db_habit.id,
                    "text": short_text,
                    "icon": mapped_icon,
                    "priority": h.get("priority", "medium"),
                }
            )

        return recs
