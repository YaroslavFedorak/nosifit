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

export interface SetEntry {
  reps?: number | null;
  duration_sec?: number | null;
  load?: number | null;
}

export interface LoggedExercise {
  id: string;
  name: string;
  slug: string | null;
  measurement_type: "reps" | "duration";
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

export interface TrainingToday {
  sessionId: string | null;
  plan: Array<{ id: number; name: string }>;
  exercises: LoggedExercise[];
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
  measurement_type: "reps" | "duration";
  per_side?: boolean;
  last?: { sets: number; reps: string | null; duration_sec: number | null; load: number | null; set_entries?: SetEntry[] } | null;
}

export interface TrainingDayDetails {
  sessions: Array<{
    session_id: number;
    exercises: Array<{ name: string; slug?: string; sets: number; reps: number | string | null; load: number; duration_sec?: number | null }>;
  }>;
}

/* Nutrition */

export interface MealItem {
  id: number;
  name: string;
  amount: number;
  unit: string;
  calories: number;
  product_id: number;
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

export interface NutritionDay {
  kcal: number;
  kcal_goal: number;
  kcal_remaining: number;
  protein: number;
  protein_goal: number;
  fat: number;
  fat_goal: number;
  carb: number;
  carb_goal: number;
  goals_available: boolean;
  meals: Meal[];
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

export interface Product {
  id: number;
  name: string;
  brand: string | null;
  kcal_per_100g: number;
  protein_per_100g: number;
  fat_per_100g: number;
  carbs_per_100g: number;
  default_unit: string;
  is_favorite: boolean;
}

export type ProductSource = "all" | "fav" | "recent" | "mine";

/* Recovery */

export interface Habit {
  id: number;
  user_habit_id: number;
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

export interface RecoverySnapshot {
  recovery_score: number | null;
  sleep_score: number | null;
  training_score: number | null;
  energy_score: number | null;
  habit_score: number | null;
  sleep_duration_minutes: number | null;
  sleep_start: string | null;
  sleep_end: string | null;
  habits: Habit[];
  recommendations: { items: RecoveryTip[]; total: number };
}

export interface HabitCatalogItem {
  id: number;
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
