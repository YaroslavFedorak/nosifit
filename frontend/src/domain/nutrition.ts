import type { FoodUnit, Meal, MealCategory, NutritionPastDay, NutritionToday, Product } from "../api/types";
import { isoDay } from "../lib/format";

/** One day of the food diary, whichever endpoint it came from. */
export interface DiaryDay {
  date: string;
  isToday: boolean;
  kcal: number;
  kcalGoal: number;
  protein: number;
  proteinGoal: number;
  fat: number;
  fatGoal: number;
  carbs: number;
  carbsGoal: number;
  /** False until the profile has what the targets are calculated from. */
  hasGoals: boolean;
  meals: Meal[];
  water: number;
  waterGoal: number | null;
  /** Yesterday's calories, known for today only: the "copy yesterday" offer needs it. */
  kcalYesterday: number;
}

export function diaryFromToday(day: NutritionToday): DiaryDay {
  return {
    date: isoDay(),
    isToday: true,
    kcal: day.kcal,
    kcalGoal: day.kcal_goal,
    protein: day.protein,
    proteinGoal: day.protein_goal,
    fat: day.fat,
    fatGoal: day.fat_goal,
    carbs: day.carb,
    carbsGoal: day.carb_goal,
    hasGoals: day.goals_available && day.kcal_goal > 0,
    meals: day.meals,
    water: day.water,
    waterGoal: day.water_goal,
    kcalYesterday: day.kcal_yesterday,
  };
}

export function diaryFromPast(day: NutritionPastDay): DiaryDay {
  return {
    date: day.date,
    isToday: false,
    kcal: day.calories,
    kcalGoal: day.calorie_goal,
    protein: day.protein,
    proteinGoal: day.protein_goal,
    fat: day.fat,
    fatGoal: day.fat_goal,
    carbs: day.carbs,
    carbsGoal: day.carbs_goal,
    hasGoals: day.goals_available && day.calorie_goal > 0,
    meals: day.meals,
    water: day.water,
    waterGoal: day.water_goal,
    kcalYesterday: 0,
  };
}

/** The meal a user is most likely logging right now. */
export function mealForNow(hour = new Date().getHours()): MealCategory {
  if (hour < 11) return "breakfast";
  if (hour < 16) return "lunch";
  if (hour < 21) return "dinner";
  return "snack";
}

/** Grams behind an amount: pieces and millilitres convert through the product. */
export function gramsOf(amount: number, unit: FoodUnit, gramsPerUnit: number): number {
  return unit === "g" ? amount : amount * (gramsPerUnit || 1);
}

export interface Portion {
  kcal: number;
  protein: number;
  fat: number;
  carbs: number;
}

/** What an amount of a product adds to the day. The server computes the stored values the same way. */
export function portionOf(product: Pick<Product, "kcal_per_100g" | "protein_per_100g" | "fat_per_100g" | "carbs_per_100g" | "grams_per_unit">, amount: number, unit: FoodUnit): Portion {
  const factor = gramsOf(amount, unit, product.grams_per_unit) / 100;
  return {
    kcal: product.kcal_per_100g * factor,
    protein: product.protein_per_100g * factor,
    fat: product.fat_per_100g * factor,
    carbs: product.carbs_per_100g * factor,
  };
}

/** The amount a product is offered at first: 100 g or ml, or one piece. */
export const defaultAmount = (unit: FoodUnit): number => (unit === "pcs" ? 1 : 100);

/** How far one press of the stepper moves an amount. */
export const amountStep = (unit: FoodUnit): number => (unit === "pcs" ? 1 : 10);

export const MAX_AMOUNT = 5000;
