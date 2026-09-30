import { NutritionAPI, } from "../api.js";
import { closeModal, openModal, } from "./modal.js";
function getInputValue(id) {
    const element = document.getElementById(id);
    return element?.value ?? "";
}
function setInputValue(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.value = value;
    }
}
export function setupMealModals(onRefresh) {
    document.getElementById("close-edit-meal")?.addEventListener("click", () => {
        closeModal("modal-edit-meal");
    });
    document.getElementById("save-edit-meal")?.addEventListener("click", async () => {
        const id = getInputValue("edit-meal-id");
        const name = getInputValue("edit-meal-name").trim();
        if (!id || !name) {
            return;
        }
        await NutritionAPI.updateMeal(Number(id), {
            name,
            category: getInputValue("edit-meal-category"),
            time: getInputValue("edit-meal-time") || null,
        });
        closeModal("modal-edit-meal");
        await onRefresh();
    });
}
