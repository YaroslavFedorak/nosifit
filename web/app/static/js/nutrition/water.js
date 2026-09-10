import { NutritionAPI, } from "./api.js";
const waterWidget = document.getElementById("water-widget");
const waterCurrent = document.getElementById("water-current");
const waterProgress = document.getElementById("water-progress");
let currentWater = 0;
let recommendedWater = 0;
function updateWaterVisual() {
    if (!waterWidget ||
        !waterCurrent ||
        !waterProgress) {
        return;
    }
    if (recommendedWater <= 0) {
        waterWidget.style.setProperty("--fill", "0");
        waterWidget.style.setProperty("--overflow", "0");
        waterWidget.classList.remove("is-overflowing");
        waterCurrent.textContent =
            currentWater.toFixed(1);
        waterProgress.textContent =
            "Рекомендація недоступна";
        return;
    }
    const ratio = currentWater / recommendedWater;
    const fillPercent = Math.min(ratio, 1) * 80;
    const overflowRatio = Math.min(Math.max(ratio - 1, 0), 1);
    waterWidget.style.setProperty("--fill", fillPercent.toFixed(1));
    waterWidget.style.setProperty("--overflow", overflowRatio.toFixed(2));
    waterWidget.classList.toggle("is-overflowing", ratio > 1);
    waterCurrent.textContent =
        currentWater.toFixed(1);
    waterProgress.textContent =
        `${Math.round(ratio * 100)}% від рекомендованого`;
}
function applyWaterData(data) {
    currentWater =
        Number(data.amount ?? 0);
    recommendedWater =
        Number(data.recommended ?? 0);
    updateWaterVisual();
}
async function loadWater() {
    try {
        const data = await NutritionAPI.getWater();
        applyWaterData(data);
    }
    catch (error) {
        console.error("Failed to load water:", error);
    }
}
document.addEventListener("nutrition:water-updated", () => {
    void loadWater();
});
void loadWater();
