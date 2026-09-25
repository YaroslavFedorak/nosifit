import { nutrition_t, } from "../../i18n/index.js";
function safeSet(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent =
            String(value);
    }
}
export function renderBalance(data) {
    safeSet("kcal-main-value", data.kcal ?? 0);
    safeSet("kcal-main-goal", nutrition_t("balance.kcalGoal", {
        value: data.kcal_goal ?? 0,
    }));
    safeSet("macro-protein-value", `${data.protein ?? 0} / ${data.protein_goal ?? 0} ${nutrition_t("units.grams")}`);
    safeSet("macro-protein-percent", `${data.protein_percent ?? 0}%`);
    safeSet("macro-fat-value", `${data.fat ?? 0} / ${data.fat_goal ?? 0} ${nutrition_t("units.grams")}`);
    safeSet("macro-fat-percent", `${data.fat_percent ?? 0}%`);
    safeSet("macro-carb-value", `${data.carb ?? 0} / ${data.carb_goal ?? 0} ${nutrition_t("units.grams")}`);
    safeSet("macro-carb-percent", `${data.carb_percent ?? 0}%`);
    safeSet("kcal-balance-label", `${data.kcal_balance ?? 0} ${nutrition_t("units.kcal")}`);
    safeSet("kcal-balance-status", data.balance_status ??
        nutrition_t("balance.noStatus"));
    safeSet("kcal-diff", `${data.kcal_diff_label ?? 0} ${nutrition_t("units.kcal")}`);
    safeSet("protein-diff", `${data.protein_diff_label ?? 0} ${nutrition_t("units.proteinShort")}`);
    safeSet("fat-diff", `${data.fat_diff_label ?? 0} ${nutrition_t("units.fatShort")}`);
    safeSet("carb-diff", `${data.carb_diff_label ?? 0} ${nutrition_t("units.carbsShort")}`);
    safeSet("water-today", `${data.water ?? 0} ${nutrition_t("units.liters")}`);
    safeSet("water-goal", `${data.water_goal ?? 0} ${nutrition_t("units.liters")}`);
    if (data.current_weight != null) {
        safeSet("weight-current", `${data.current_weight} ${nutrition_t("units.kg")}`);
    }
}
