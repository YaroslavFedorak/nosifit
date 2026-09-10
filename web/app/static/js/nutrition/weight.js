import { NutritionAPI, } from "./api.js";
const widget = document.getElementById("weight-widget");
const currentElement = document.getElementById("weight-current");
const bmiElement = document.getElementById("weight-bmi");
function renderWeight(data) {
    if (!currentElement) {
        return;
    }
    if (data.weight === null ||
        !Number.isFinite(data.weight)) {
        currentElement.textContent = "—";
    }
    else {
        currentElement.textContent =
            data.weight.toFixed(1);
    }
    if (!bmiElement) {
        return;
    }
    if (data.bmi === null ||
        !Number.isFinite(data.bmi)) {
        bmiElement.textContent = "—";
        return;
    }
    bmiElement.textContent =
        data.bmi.toFixed(1);
}
async function loadWeight() {
    if (!widget) {
        return;
    }
    try {
        const data = await NutritionAPI.getWeight();
        renderWeight(data);
    }
    catch (error) {
        console.error("Failed to load weight:", error);
    }
}
document.addEventListener("nutrition:weight-updated", () => {
    void loadWeight();
});
void loadWeight();
