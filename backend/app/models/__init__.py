from backend.app.models.user import User
from backend.app.models.user_equipment import UserEquipment
from backend.app.models.oauth_account import OAuthAccount

# Nutrition subsystem
from backend.app.models.nutrition.plan import NutritionPlan
from backend.app.models.nutrition.meal import Meal
from backend.app.models.nutrition.meal_item import MealItem
from backend.app.models.nutrition.category import Category
from backend.app.models.nutrition.user_goals import UserGoals
from backend.app.models.nutrition.user_weight import UserWeight
from backend.app.models.nutrition.saved_meal import SavedMeal
from backend.app.models.nutrition.user_water import UserWater

# Training Session Engine
from backend.app.models.training_session import TrainingSession, SessionExercise
from backend.app.training.models.user_pref import UserPreference

# Onboarding subsystem
from backend.app.models.user_profile import UserProfile
from backend.app.models.user_goals import UserTrainingGoals
from backend.app.models.injury import Injury
from backend.app.models.user_injury import UserInjury

# Recovery subsystem
from backend.app.models.recovery.sleep_entry import SleepEntry
from backend.app.models.recovery.habit import RecoveryHabit
from backend.app.models.recovery.user_habit import UserRecoveryHabit
from backend.app.models.recovery.habit_log import RecoveryHabitLog
from backend.app.models.recovery.daily_recovery_snapshot import DailyRecoverySnapshot

