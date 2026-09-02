from web.app.models.user import User
from web.app.models.user_equipment import UserEquipment
from web.app.models.oauth_account import OAuthAccount

# Nutrition subsystem
from web.app.models.nutrition.plan import NutritionPlan
from web.app.models.nutrition.meal import Meal
from web.app.models.nutrition.meal_item import MealItem
from web.app.models.nutrition.category import Category
from web.app.models.nutrition.user_goals import UserGoals
from web.app.models.nutrition.user_weight import UserWeight
from web.app.models.nutrition.saved_meal import SavedMeal
from web.app.models.nutrition.user_water import UserWater

# Training Session Engine
from web.app.models.training_session import TrainingSession, SessionExercise
from web.app.training_engine.models.user_pref import UserPreference

# Onboarding subsystem
from web.app.models.user_profile import UserProfile
from web.app.models.user_goals import UserTrainingGoals
from web.app.models.injury import Injury
from web.app.models.user_injury import UserInjury

# Recovery subsystem
from web.app.models.recovery.sleep_entry import SleepEntry
from web.app.models.recovery.habit import RecoveryHabit
from web.app.models.recovery.user_habit import UserRecoveryHabit
from web.app.models.recovery.habit_log import RecoveryHabitLog
from web.app.models.recovery.daily_recovery_snapshot import DailyRecoverySnapshot
