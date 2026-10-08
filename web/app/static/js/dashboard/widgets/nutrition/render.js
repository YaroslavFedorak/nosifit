import { nutrition_t } from "../../../i18n/index.js";
import { renderMealList } from "../../../nutrition/ui/mealList.js";
/** Dashboard widget: the same meal list as the Nutrition page, compact styling. */
export function renderMeals(meals, onRefresh) {
    const list = document.getElementById("dashboard-meals-list");
    if (!list)
        return;
    renderMealList(list, meals, {
        onRefresh,
        emptyText: nutrition_t("meals.emptyToday"),
    });
}
