import json
import os
from typing import List, Dict

from myapp.app import db
from myapp.app.models.recovery.habit import RecoveryHabit
from myapp.app.services.recovery.constants import RecoveryTrigger
from myapp.app.services.recovery.constants import (
    TRAINING_LOAD_HEAVY,
    TRAINING_LOAD_VERY_HEAVY,
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

        if daily_load > TRAINING_LOAD_VERY_HEAVY:
            triggers.append(RecoveryTrigger.AFTER_TRAINING.value)
        elif daily_load > TRAINING_LOAD_HEAVY:
            triggers.append(RecoveryTrigger.AFTER_TRAINING.value)

        return triggers

    def filter_habits_by_triggers(self, triggers: List[str]) -> List[Dict]:
        matched = []

        for habit in self.habits:
            habit_triggers = habit.get("recommended_when", [])
            if any(t in habit_triggers for t in triggers):
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

        def sort_key(h):
            return (
                -h["points"],
                category_order.get(h["category"], 99),
                h["slug"],
            )

        return sorted(habits, key=sort_key)

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

        habits = self.filter_habits_by_triggers(triggers)
        habits = self.sort_habits(habits)

        recs = []

        for h in habits[:5]:
            db_habit = RecoveryHabit.query.filter_by(slug=h["slug"]).first()
            if not db_habit:
                continue

            recs.append(
                {
                    "habit_id": db_habit.id,
                    "text": h["name"],
                    "icon": h["icon"],
                    "priority": h.get("priority", "medium"),
                }
            )

        return recs
