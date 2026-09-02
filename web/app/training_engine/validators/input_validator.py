from typing import List


class InputValidator:
    @staticmethod
    def validate_age(age: int):
        if not (10 <= age <= 100):
            raise ValueError("Age must be between 10 and 100")

    @staticmethod
    def validate_weight(weight: float):
        if not (20 <= weight <= 300):
            raise ValueError("Weight must be between 20 and 300 kg")

    @staticmethod
    def validate_height(height: float):
        if not (100 <= height <= 250):
            raise ValueError("Height must be between 100 and 250 cm")

    @staticmethod
    def validate_activity(activity: float):
        if not (1.0 <= activity <= 2.5):
            raise ValueError("Activity level must be between 1.0 and 2.5")

    @staticmethod
    def validate_goal(goal: str):
        allowed = ["gain", "lose", "maintain", "strength", "endurance"]
        if goal not in allowed:
            raise ValueError(f"Goal must be one of: {allowed}")

    @staticmethod
    def validate_environment(env: str):
        allowed = ["home", "outdoor", "gym"]
        if env not in allowed:
            raise ValueError(f"Environment must be one of: {allowed}")

    @staticmethod
    def validate_weak_points(points: List[str]):
        for p in points:
            if not isinstance(p, str):
                raise ValueError("Weak points must be strings")

    @staticmethod
    def validate_all(profile):
        InputValidator.validate_age(profile.age)
        InputValidator.validate_weight(profile.weight)
        InputValidator.validate_height(profile.height)
        InputValidator.validate_activity(profile.activity)
        InputValidator.validate_goal(profile.goal)
        InputValidator.validate_environment(profile.environment)
        InputValidator.validate_weak_points(profile.weak_points)
