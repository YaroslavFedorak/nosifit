/** Only the fields the interface reads. The API sends more. */

export type MealCategory = "breakfast" | "lunch" | "dinner" | "snack";
export const MEAL_CATEGORIES: MealCategory[] = ["breakfast", "lunch", "dinner", "snack"];

/* Dashboard */

export interface DashboardToday {
  date: string;
  daily_score: number | null;
  training: { completed: boolean; duration: number; exercise_count: number; score: number | null };
  nutrition: { calories: number; protein: number; water: number; score: number | null };
  recovery: { habits_completed: number; habits_total: number; sleep_hours: number; score: number | null };
}

export interface DashboardDay {
  date: string;
  daily_score: number | null;
  level: number;
}

export interface Recommendation {
  id: string;
  type: string;
  category: string;
  title: string | null;
  title_key: string | null;
  description: string;
  description_key: string | null;
  params: Record<string, string | number>;
  slug: string | null;
}

export interface DashboardRecommendation {
  daily: Recommendation | null;
  categories: { training: Recommendation | null; nutrition: Recommendation | null; recovery: Recommendation | null };
}

/* Training */

export type Measurement = "reps" | "duration";

export interface SetEntry {
  reps?: number | null;
  duration_sec?: number | null;
  load?: number | null;
}

/** An exercise of today's workout, with the sets that were done. */
export interface LoggedExercise {
  id: string;
  name: string;
  slug: string | null;
  measurement_type: Measurement;
  sets: number;
  reps: string | number | null;
  duration_sec: number | null;
  load: number | null;
  per_side?: boolean;
  accepts_load?: boolean;
  rpe?: number | null;
  set_entries?: SetEntry[];
}

export interface TrainingSession {
  id: number;
  status: string;
  exercises: LoggedExercise[];
  totals: { exercises: number; sets: number };
}

/** An exercise as a plan stores it: what to do, not what was done. */
export interface PlanEntry {
  exercise: { id: string | number; name: string; slug: string | null; measurement_type: Measurement };
  measurement_type: Measurement;
  sets: number | null;
  reps: string | number | null;
  duration_sec: number | null;
  per_side?: boolean;
  load: number | null;
}

export interface TrainingToday {
  sessionId: string | null;
  plan: Array<{ id: number; name: string }>;
  exercises: PlanEntry[];
}

export type Weekday = "mon" | "tue" | "wed" | "thu" | "fri" | "sat" | "sun";
export const WEEKDAYS: Weekday[] = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];

export interface PlanDay {
  exercises: PlanEntry[];
  location?: string | null;
  equipment?: string[] | null;
}

export interface Plan {
  id: number;
  name: string;
  is_active: boolean;
  /** Older plans stored a bare list per day. */
  days: Partial<Record<Weekday, PlanDay | PlanEntry[]>>;
}

export interface PlanWeekDay {
  key: Weekday;
  date: string;
  exercises: number;
  rest: boolean;
  completed: boolean;
  is_today: boolean;
}

export interface PlanWeek {
  plan_id: number;
  days: PlanWeekDay[];
}

export interface PlanDraft {
  days: Partial<Record<Weekday, PlanDay>>;
  notes?: Array<{ code: string }>;
}

export interface WeeklyMuscle {
  muscle: string;
  sets: number;
  target_sets: number;
}

export interface TrainingHeatmapDay {
  date: string;
  hard_sets: number;
  intensity_percent: number;
}

export interface GuidanceItem {
  kind: string;
  muscle: string;
  action: string | null;
  params: Record<string, string | number>;
  reasons: string[];
}

export interface RecommendedExercise {
  exercise: string;
  slug: string | null;
  sets: number | null;
  reps: string | number | null;
  duration_sec: number | null;
  measurement_type: string;
  target_muscles: string[];
  reasons: string[];
}

export interface TrainingRecommendations {
  guidance?: { verdict: string; title: string; message: string; muscles: GuidanceItem[]; warnings: GuidanceItem[] };
  recommended_exercises?: RecommendedExercise[];
}

export interface ExerciseOption {
  id: string;
  name: string;
  slug: string | null;
  measurement_type: Measurement;
  per_side?: boolean;
  accepts_load?: boolean;
  last?: { sets: number; reps: string | null; duration_sec: number | null; load: number | null; set_entries?: SetEntry[] } | null;
}

export interface TrainingDayDetails {
  sessions: Array<{
    session_id: number;
    exercises: Array<{ name: string; slug?: string; sets: number; reps: number | string | null; load: number; duration_sec?: number | null }>;
  }>;
}

/* Nutrition */

export type FoodUnit = "g" | "ml" | "pcs";

export interface MealItem {
  id: number;
  product_id: number;
  name: string;
  amount: number;
  unit: FoodUnit;
  calories: number;
  protein: number;
  fat: number;
  carbs: number;
  dish_name?: string | null;
}

export interface Meal {
  id: number;
  category: MealCategory;
  time: string | null;
  items: MealItem[];
  total_calories: number;
  total_protein: number;
  total_fat: number;
  total_carbs: number;
}

/** GET /nutrition/day: today. */
export interface NutritionToday {
  kcal: number;
  kcal_goal: number;
  protein: number;
  protein_goal: number;
  fat: number;
  fat_goal: number;
  carb: number;
  carb_goal: number;
  goals_available: boolean;
  meals: Meal[];
  water: number;
  water_goal: number | null;
  kcal_yesterday: number;
}

/** GET /nutrition/day/<date>: any other day. */
export interface NutritionPastDay {
  date: string;
  calories: number;
  protein: number;
  fat: number;
  carbs: number;
  calorie_goal: number;
  protein_goal: number;
  fat_goal: number;
  carbs_goal: number;
  goals_available: boolean;
  meals: Meal[];
  water: number;
  water_goal: number | null;
}

export interface NutritionTip {
  type: string;
  priority: string;
  title_key: string;
  message_key: string;
  params: Record<string, string | number>;
}

export interface NutritionHeatmapDay {
  date: string;
  level: number;
  kcal: number;
  percent: number;
}

export interface NutritionStats {
  kcal: { labels: string[]; values: Array<number | null>; logged: boolean[] };
  weight: { labels: string[]; values: number[] };
  avg_kcal: number | null;
  avg_kcal_days: number;
  goal_kcal: number | null;
  current_weight: number | null;
  weight_trend: "insufficient_data" | "stable" | "increasing" | "decreasing";
  weight_trend_detail?: { change_kg?: number | null };
}

export interface Product {
  id: number;
  name: string;
  brand: string | null;
  category: string;
  barcode: string | null;
  kcal_per_100g: number;
  protein_per_100g: number;
  fat_per_100g: number;
  carbs_per_100g: number;
  default_unit: FoodUnit;
  grams_per_unit: number;
  is_favorite: boolean;
  is_own: boolean;
}

export interface NewProduct {
  name: string;
  brand?: string;
  kcal_per_100g: number;
  protein_per_100g: number;
  fat_per_100g: number;
  carbs_per_100g: number;
  default_unit: FoodUnit;
  grams_per_unit: number;
  barcode?: string;
}

export interface Dish {
  id: number;
  name: string;
  items: Array<{ product_id: number; name: string; amount: number; unit: FoodUnit; calories: number }>;
  totals: { grams: number; calories: number; protein: number; fat: number; carbs: number };
}

export interface BarcodeLookup {
  barcode: string;
  status: "found" | "not_found";
  source: string;
  /** Already in the catalog. */
  product?: Product;
  /** Found outside the catalog: can be imported. */
  preview?: { name?: string | null; brand?: string | null; kcal_per_100g?: number | null };
}

export interface WaterDay {
  amount: number;
  recommended: number | null;
}

export interface WeightInfo {
  weight: number | null;
  bmi: number | null;
}

/* Recovery */

export interface Habit {
  id: number;
  user_habit_id: number;
  slug: string;
  name: string;
  category: string;
  completed: boolean;
}

export interface RecoveryTip {
  id: string;
  type: string;
  title_key: string;
  message_key: string;
  params: Record<string, string | number>;
  priority: string;
}

/** The newest recovery snapshot; `date` says which day it describes. */
export interface RecoverySnapshot {
  date: string;
  recovery_score: number | null;
  sleep_score: number | null;
  training_score: number | null;
  energy_score: number | null;
  habit_score: number | null;
  sleep_duration_minutes: number | null;
  sleep_start: string | null;
  sleep_end: string | null;
  recommendations: { items: RecoveryTip[]; total: number };
}

export interface HabitCatalogItem {
  id: number;
  slug: string;
  name: string;
  category: string;
  description: string;
  premium_only: boolean;
}

export interface RecoveryHeatmapDay {
  date: string;
  level: number;
  recovery_score: number | null;
}

export interface RecoveryDayDetails {
  has_data: boolean;
  recovery: { score: number | null };
  sleep: { duration_minutes: number | null };
  habits: { completed: number; total: number };
}

/* Account */

export interface AccountProfile {
  age: number | null;
  gender: string | null;
  height: number | null;
  weight: number | null;
  activity: string | null;
  goal: string | null;
  experience: string | null;
  workouts_per_week: number | null;
  training_location: string | null;
  wants_nutrition: boolean;
  wants_recovery: boolean;
}

export interface AccountSummary {
  user: { id: number; name: string; email: string; member_since: string | null };
  profile: AccountProfile;
  options: {
    genders: string[];
    goals: string[];
    /** Stored value and the key of its label. */
    activities: Array<[string, string]>;
    experiences: string[];
    locations: string[];
  };
  sign_in: {
    has_password: boolean;
    google: boolean;
    github: boolean;
    telegram: boolean;
    telegram_username: string | null;
    telegram_connect_url: string | null;
    method_count: number;
  };
}
