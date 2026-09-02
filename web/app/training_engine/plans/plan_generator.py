import json
from pathlib import Path
from web.app.training_engine.models.training_plan import (
    TrainingPlan as ORMTrainingPlan,
)
from web.app.training_engine.models.training_day import TrainingDay as ORMTrainingDay
from web.app.training_engine.models.exercise import Exercise
from .plan_validator import PlanValidator


class PlanGenerator:
    def __init__(self, profile_snapshot):
        self.profile = profile_snapshot

    def _template_path(self, split: str) -> str:
        base = Path(__file__).resolve().parents[1] / "data" / "templates" / "splits"
        return str(base / f"{split}.json")

    def _load_template(self, split: str):
        path = self._template_path(split)
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _choose_split(self, workouts_per_week: int) -> str:
        if workouts_per_week <= 1:
            return "full_body"
        if workouts_per_week == 2:
            return "full_body"
        if workouts_per_week == 3:
            return "full_body"
        if workouts_per_week == 4:
            return "upper_lower"
        if workouts_per_week == 5:
            return "ppl"
        if workouts_per_week == 6:
            return "ppl"
        return "hybrid"

    def generate(self, week: int = 1):
        split = self._choose_split(self.profile.workouts_per_week)
        tpl = self._load_template(split)
        days_def = tpl.get("days", {})

        plan = ORMTrainingPlan(
            user_id=getattr(self.profile, "user_id", None),
            name=tpl.get("name", "Training Plan"),
            is_active=False,
        )

        for key, day_cfg in days_def.items():
            day = ORMTrainingDay(
                day_name=key,
                name=day_cfg.get("name", key),
                environment=[self.profile.environment],
                exercises=[],
            )

            for ex_def in day_cfg.get("exercises", []):
                slug = ex_def.get("id")
                if not slug:
                    continue

                ex = Exercise.query.filter_by(slug=slug).first()
                if not ex:
                    continue

                day.add_exercise(
                    exercise=ex,
                    sets=ex_def.get("sets", 3),
                    reps=ex_def.get("reps", "8-12"),
                )

            plan.add_day(key, day)

        PlanValidator.validate(plan.days)
        return plan
