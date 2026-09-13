import { NutritionAPI, } from "../../../nutrition/api.js";
import { renderMeals, } from "./render.js";
import { setNutritionDay, } from "./state.js";
import { setupMealModals, } from "../../modals/nutrition/meals.js";
import { setupItemModals, } from "../../modals/nutrition/items.js";
import { setupWaterModal, } from "../../modals/nutrition/water.js";
import { setupWeightModal, } from "../../modals/nutrition/weight.js";
function renderWater(value) {
    const element = document.getElementById("dashboard-water");
    if (!element) {
        return;
    }
    const water = Number(value ?? 0);
    if (!Number.isFinite(water)) {
        element.textContent = "—";
        return;
    }
    element.textContent =
        `${Math.round(water)} мл`;
}
function renderWeight(data) {
    const element = document.getElementById("dashboard-weight");
    if (!element) {
        return;
    }
    if (data.weight === null ||
        !Number.isFinite(data.weight)) {
        element.textContent = "—";
        return;
    }
    element.textContent =
        `${data.weight.toFixed(1)} кг`;
}
async function loadNutrition() {
    try {
        const data = await NutritionAPI.getDay();
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
        const data = await NutritionAPI.getWeight();
        renderWeight(data);
    }
    catch (error) {
        console.error("Failed to load dashboard weight:", error);
    }
}
function initializeNutritionWidget() {
    setupMealModals(loadNutrition);
    setupItemModals(loadNutrition);
    setupWaterModal(loadNutrition);
    setupWeightModal(loadWeight);
    void loadNutrition();
    void loadWeight();
}
document.addEventListener("DOMContentLoaded", initializeNutritionWidget);
