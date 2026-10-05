import { nutrition_t } from "../../i18n/index.js";
import type { Meal } from "../types.js";
import { renderMealList } from "./mealList.js";

type RefreshCallback = () => Promise<void> | void;

function renderMealsSummary(meals: Meal[]): void {
    const element = document.getElementById("meals-day-summary");
    if (!element) return;

    const calories = meals.reduce((sum, meal) => sum + Number(meal.total_calories ?? 0), 0);

    element.innerHTML = "";

    const value = document.createElement("span");
    value.className = "meals-summary-value";
    value.textContent = String(Math.round(calories));

    const unit = document.createElement("span");
    unit.className = "meals-summary-unit";
    unit.textContent = nutrition_t("units.kcal");

    const divider = document.createElement("span");
    divider.className = "meals-summary-divider";

    const count = document.createElement("span");
    count.className = "meals-summary-count";
    count.textContent = nutrition_t("meals.count", { count: meals.length });

    element.append(value, unit, divider, count);
}

/** Nutrition page: meal list + calories summary in the widget header. */
export function renderMeals(meals: Meal[], onRefresh: RefreshCallback): void {
    const list = document.getElementById("meals-list");
    if (!list) return;

    renderMealsSummary(meals);
    renderMealList(list, meals, { onRefresh });
}
