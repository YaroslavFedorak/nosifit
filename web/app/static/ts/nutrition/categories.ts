import { nutrition_t } from "../i18n/index.js";

export const MEAL_CATEGORIES = ["breakfast", "lunch", "dinner", "snack"] as const;

export type MealCategory = typeof MEAL_CATEGORIES[number];

// Old rows stored Ukrainian labels. The backend migrates them, but keep the
// aliases so a stale response never shows up untranslated.
const ALIASES: Record<string, MealCategory> = {
    "сніданок": "breakfast",
    "обід": "lunch",
    "вечеря": "dinner",
    "перекус": "snack",
};

export function normalizeMealCategory(value: string | null | undefined): MealCategory | null {
    const normalized = (value ?? "").trim().toLowerCase();
    if ((MEAL_CATEGORIES as readonly string[]).includes(normalized)) {
        return normalized as MealCategory;
    }
    return ALIASES[normalized] ?? null;
}

export function mealCategoryLabel(value: string | null | undefined): string {
    const category = normalizeMealCategory(value);
    return category
        ? nutrition_t(`meal_categories.${category}`)
        : (value || nutrition_t("meal_categories.default"));
}

/** A sensible default for a new meal based on the current time. */
export function suggestMealCategory(now: Date = new Date()): MealCategory {
    const hour = now.getHours();
    if (hour >= 5 && hour < 11) return "breakfast";
    if (hour >= 11 && hour < 16) return "lunch";
    if (hour >= 17 && hour < 22) return "dinner";
    return "snack";
}

export function unitLabel(unit: string | null | undefined): string {
    const value = unit ?? "g";
    return ["g", "ml", "pcs"].includes(value)
        ? nutrition_t(`catalog.units.${value}`)
        : value;
}

export function formatAmount(amount: number | null | undefined, unit: string | null | undefined): string {
    if (amount == null || !Number.isFinite(Number(amount))) return "—";
    const value = Number(amount);
    const text = Number.isInteger(value) ? String(value) : value.toFixed(1).replace(/\.0$/, "");
    return `${text} ${unitLabel(unit)}`;
}
