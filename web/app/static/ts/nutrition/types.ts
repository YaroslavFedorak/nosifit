export interface MealItem {
    id: number;
    name: string;

    calories: number;
    protein: number;
    fat: number;
    carbs: number;
    fiber?: number;

    weight?: number | null;
    category_label?: string | null;
    category_id?: number | null;
}


export interface Meal {
    id: number;
    name: string;

    category?: string | null;
    time?: string | null;

    total_calories?: number;
    total_protein?: number;
    total_fat?: number;
    total_carbs?: number;

    items?: MealItem[];
}


export interface NutritionDay {
    kcal?: number;
    kcal_goal?: number;

    protein?: number;
    protein_goal?: number;
    protein_percent?: number;

    fat?: number;
    fat_goal?: number;
    fat_percent?: number;

    carb?: number;
    carb_goal?: number;
    carb_percent?: number;

    kcal_balance?: number;
    balance_status?: string;

    kcal_diff_label?: number;
    protein_diff_label?: number;
    fat_diff_label?: number;
    carb_diff_label?: number;

    water?: number;
    water_goal?: number;

    current_weight?: number | null;

    meals: Meal[];
}


export interface MealPayload {
    name: string;
    category: string;
    time?: string | null;
}


export interface MealItemPayload {
    meal_id: number;
    name: string;

    weight?: number | null;

    calories?: number;
    protein?: number;
    fat?: number;
    carbs?: number;
    fiber?: number;

    category_label?: string | null;
    category_id?: number | null;
}


export interface WeightPayload {
    weight: number;
}


export interface WaterPayload {
    amount: number;
}


export type RecommendationType =
    | "calories"
    | "protein"
    | "fat"
    | "carbs"
    | "fiber"
    | "quality"
    | "balance"
    | "protein_progress"
    | "macro_balance";


export type RecommendationPriority =
    | "low"
    | "medium"
    | "high";


export interface NutritionRecommendation {
    type: RecommendationType;
    title: string;
    message: string;
    priority: RecommendationPriority;
}


export type NutritionDayProgress =
    | "morning"
    | "day"
    | "evening"
    | "late";


export interface NutritionRecommendationSummary {
    calories: number;
    calories_goal: number;

    protein: number;
    protein_goal: number;

    fat: number;
    fat_goal: number;

    carbs: number;
    carbs_goal: number;

    fiber: number;
    fiber_goal: number;

    quality_score: number;

    day_progress: NutritionDayProgress;
}


export interface NutritionRecommendationResponse {
    recommendations: NutritionRecommendation[];
    summary: NutritionRecommendationSummary;
}