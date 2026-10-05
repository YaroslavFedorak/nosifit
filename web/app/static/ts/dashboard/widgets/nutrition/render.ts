import { nutrition_t } from "../../../i18n/index.js";
import type { Meal } from "../../../nutrition/types.js";
import { renderMealList } from "../../../nutrition/ui/mealList.js";

type RefreshCallback = () => Promise<void> | void;

/** Dashboard widget: the same meal list as the Nutrition page, compact styling. */
export function renderMeals(meals: Meal[], onRefresh: RefreshCallback): void {
    const list = document.getElementById("dashboard-meals-list");
    if (!list) return;

    renderMealList(list, meals, {
        onRefresh,
        emptyText: nutrition_t("meals.emptyToday"),
    });
}
