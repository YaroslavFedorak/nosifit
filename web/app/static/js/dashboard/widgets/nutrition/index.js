import { NutritionAPI } from "../../../nutrition/api.js";
import { setupItemModals } from "../../../nutrition/modals/items.js";
import { setupMealModals } from "../../../nutrition/modals/meals.js";
import { setupWaterModal } from "../../../nutrition/modals/water.js";
import { setupWeightModal } from "../../../nutrition/modals/weight.js";
import { getLocale, loadTranslations, nutrition_t } from "../../../i18n/index.js";
import { renderMeals } from "./render.js";
import { setNutritionDay } from "./state.js";
function renderWater(value) {
    const element = document.getElementById("dashboard-water");
    if (!element)
        return;
    const liters = Number(value ?? 0);
    element.textContent = Number.isFinite(liters)
        ? `${liters.toFixed(1)} ${nutrition_t("units.liters")}`
        : "—";
}
function renderWeight(data) {
    const element = document.getElementById("dashboard-weight");
    if (!element)
        return;
    element.textContent = data.weight !== null && Number.isFinite(data.weight)
        ? `${Number(data.weight).toFixed(1)} ${nutrition_t("units.kg")}`
        : "—";
}
async function loadNutrition() {
    try {
        const data = await NutritionAPI.getDay(getLocale());
        setNutritionDay(data);
        renderWater(data.water);
        renderMeals(data.meals, loadNutrition);
    }
    catch (error) {
        console.error("Failed to load dashboard nutrition:", error);
    }
}
async function loadWeight() {
    try {
        renderWeight(await NutritionAPI.getWeight());
    }
    catch (error) {
        console.error("Failed to load dashboard weight:", error);
    }
}
async function initializeNutritionWidget() {
    // The modals and the meal list are shared with the Nutrition page and
    // read their texts from the "nutrition" namespace.
    try {
        await loadTranslations("nutrition");
    }
    catch (error) {
        console.error("Failed to load nutrition translations:", error);
    }
    setupMealModals(loadNutrition);
    setupItemModals(loadNutrition);
    setupWaterModal(loadNutrition, ["dashboard-add-water"]);
    setupWeightModal(loadWeight, ["dashboard-open-update-weight"]);
    void loadNutrition();
    void loadWeight();
}
document.addEventListener("DOMContentLoaded", () => {
    void initializeNutritionWidget();
});
