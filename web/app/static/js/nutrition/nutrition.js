import { NutritionAPI, } from "./api.js";
import { renderBalance, } from "./ui/balance.js";
import { renderMeals, } from "./ui/meals.js";
import { setupMealModals, } from "./modals/meals.js";
import { setupItemModals, } from "./modals/items.js";
import { setupWaterModal, } from "./modals/water.js";
import { setupWeightModal, } from "./modals/weight.js";
import { setupNutritionHeatmapModals, } from "./modals/heatmap.js";
import { initializeNutritionHeatmap, } from "./heatmap.js";
import { loadNutritionRecommendations, } from "./recommendations.js";
function setTodayDate() {
    const element = document.getElementById("current-date");
    if (!element) {
        return;
    }
    const today = new Date();
    element.textContent =
        today.toLocaleDateString("uk-UA", {
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
        });
}
async function loadNutritionDay() {
    try {
        const data = await NutritionAPI.getDay();
        renderBalance(data);
        renderMeals(data.meals, loadNutritionDay);
        await loadNutritionRecommendations();
        document.dispatchEvent(new CustomEvent("nutrition:heatmap-reload"));
    }
    catch (error) {
        console.error("Failed to load nutrition data:", error);
    }
}
function initializeNutritionPage() {
    setTodayDate();
    setupNutritionHeatmapModals();
    setupMealModals(loadNutritionDay);
    setupItemModals(loadNutritionDay);
    setupWaterModal(loadNutritionDay);
    setupWeightModal(loadNutritionDay);
    initializeNutritionHeatmap();
    void loadNutritionDay();
}
document.addEventListener("DOMContentLoaded", initializeNutritionPage);
