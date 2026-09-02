from dataclasses import dataclass
from typing import List, Optional


@dataclass
class UserProfileSnapshot:
    age: int
    sex: str
    weight: Optional[float]
    height: Optional[float]
    activity: Optional[str]
    goal: str
    experience: str
    workouts_per_week: int
    environment: str
    weak_points: List[str]
    strong_points: List[str]
    user_id: int | None = None
