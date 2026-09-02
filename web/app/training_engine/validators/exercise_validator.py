from web.app.training_engine.models.exercise import Exercise


class ExerciseValidator:
    @staticmethod
    def validate(ex: Exercise):
        if not getattr(ex, "id", None):
            raise ValueError("Exercise must have a valid ID")

        if not getattr(ex, "name", None):
            raise ValueError("Exercise must have a name")

        muscles_primary = getattr(ex, "muscles_primary", None)
        if not muscles_primary:
            raise ValueError("Exercise must have at least one primary muscle")

        difficulty = getattr(ex, "difficulty", None)
        if difficulty is None or difficulty < 1 or difficulty > 10:
            raise ValueError("Difficulty must be between 1 and 10")

        risk_level = getattr(ex, "risk_level", None)
        if risk_level is None or risk_level < 1 or risk_level > 5:
            raise ValueError("Risk level must be between 1 and 5")

        environment = getattr(ex, "environment", None)
        if not isinstance(environment, list):
            raise ValueError("Environment must be a list")

        return True
