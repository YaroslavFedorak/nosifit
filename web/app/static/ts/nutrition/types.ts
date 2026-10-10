export type NutritionUnit = "g" | "ml" | "pcs";

export interface Product {
    id: number;
    name: string;
    brand?: string | null;
    source: "system" | "user" | "imported";
    barcode?: string | null;
    kcal_per_100g: number;
    protein_per_100g: number;
    fat_per_100g: number;
    carbs_per_100g: number;
    /** null = unknown (not 0). */
    fiber_per_100g: number | null;
    sugar_per_100g?: number | null;
    saturated_fat_per_100g?: number | null;
    salt_per_100g?: number | null;
    liquid_ml_per_100g: number;
    default_unit: NutritionUnit;
    grams_per_unit: number;
    /** Where catalog values come from, e.g. "ciqual_2020" / "13039". */
    data_source?: string | null;
    source_ref?: string | null;
    verified?: boolean;
    is_favorite: boolean;
    /** The user's own product: can be edited and deleted. */
    is_own?: boolean;
}

export interface ProductPayload {
    name: string;
    brand?: string | null;
    locale?: string;
    barcode?: string | null;
    kcal_per_100g: number;
    protein_per_100g: number;
    fat_per_100g: number;
    carbs_per_100g: number;
    /** Optional: leave out (or null) when unknown. */
    fiber_per_100g?: number | null;
    sugar_per_100g?: number | null;
    liquid_ml_per_100g?: number;
    default_unit: NutritionUnit;
    grams_per_unit: number;
}

/** External product data from a barcode lookup, normalized to per 100 g / ml. */
export interface BarcodePreview {
    barcode: string;
    name: string | null;
    brand: string | null;
    /** null = missing or invalid, never a stand-in 0. */
    kcal_per_100g: number | null;
    protein_per_100g: number | null;
    fat_per_100g: number | null;
    carbs_per_100g: number | null;
    fiber_per_100g: number | null;
    sugar_per_100g: number | null;
    saturated_fat_per_100g: number | null;
    salt_per_100g: number | null;
    default_unit: NutritionUnit;
    grams_per_unit: number;
    basis: "100g" | "100ml";
    missing: string[];
    missing_optional: string[];
    invalid: Record<string, string>;
    warnings: string[];
    complete: boolean;
    importable: boolean;
    data_source: string;
    source_ref: string;
    verified: boolean;
}

export interface BarcodeLookupResult {
    barcode: string;
    status: "found" | "not_found";
    source: "catalog" | "open_food_facts";
    /** Set when the barcode is already in the catalog (or the user's own product). */
    product?: Product;
    /** Set for an external result: review it, then import. */
    preview?: BarcodePreview;
    stale?: boolean;
    attribution?: string;
}

export interface ProductListResponse {
    products: Product[];
    has_more?: boolean;
}

export interface MealItem {
    id: number;
    product_id?: number | null;
    name: string;
    amount?: number | null;
    unit?: NutritionUnit | null;
    weight?: number | null;
    calories: number;
    protein: number;
    fat: number;
    carbs: number;
    fiber?: number | null;
    sugar?: number | null;
    liquid_ml?: number;
    dish_id?: number | null;
    dish_name?: string | null;
}

export interface Meal {
    id: number;
    name: string;
    category?: string | null;
    date?: string | null;
    time?: string | null;
    total_calories?: number;
    total_protein?: number;
    total_fat?: number;
    total_carbs?: number;
    total_fiber?: number | null;
    total_sugar?: number | null;
    fiber_complete?: boolean;
    sugar_complete?: boolean;
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
    fiber?: number | null;
    fiber_complete?: boolean;
    fiber_goal?: number;
    sugar?: number | null;
    sugar_complete?: boolean;
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
    name?: string;
    category: string;
    time?: string | null;
    date?: string | null;
    locale?: string;
}

export interface MealItemPayload {
    meal_id: number;
    product_id?: number;
    amount?: number;
    unit?: NutritionUnit;
    locale?: string;
}

export interface EntryUpdatePayload {
    meal_id?: number;
    product_id?: number;
    amount?: number;
    unit?: NutritionUnit;
    locale?: string;
}

export interface WeightPayload {
    weight: number;
}

export interface WeightResponse {
    status?: string;
    weight: number | null;
    bmi: number | null;
}

export interface WaterPayload {
    amount: number;
}

export interface WaterResponse {
    status?: string;
    amount: number;
    recommended: number;
}

export interface NutritionHeatmapDay {
    date: string;
    kcal: number;
    protein: number;
    fat: number;
    carbs: number;
    calorie_goal: number;
    protein_goal: number;
    fat_goal: number;
    carbs_goal: number;
    percent: number;
    level: number;
    is_today: boolean;
}

export interface NutritionHeatmapResponse {
    year: number;
    days: NutritionHeatmapDay[];
}

export interface NutritionDayDetails {
    date: string;
    calories: number;
    protein: number;
    fat: number;
    carbs: number;
    fiber: number | null;
    fiber_complete?: boolean;
    sugar?: number | null;
    sugar_complete?: boolean;
    fiber_goal: number;
    calorie_goal: number;
    protein_goal: number;
    fat_goal: number;
    carbs_goal: number;
    water: number;
    water_goal: number;
    current_weight: number | null;
    meals: Meal[];
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

export type RecommendationPriority = "low" | "medium" | "high";

export interface NutritionRecommendation {
    type: RecommendationType;
    title: string;
    message: string;
    priority: RecommendationPriority;
}

export type NutritionDayProgress = "morning" | "day" | "evening" | "late";

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
