from web.app.training_engine.models.exercise import Exercise


class PlanAdapter:
    @staticmethod
    def by_slug(slug: str):
        if not slug:
            return None
        return Exercise.query.filter_by(slug=slug).first()
