import { NutritionAPI, } from "../../../nutrition/api.js";
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
    document.getElementById("dashboard-open-add-meal")?.addEventListener("click", () => {
                setInputValue("add-meal-category", "Сніданок");
        setInputValue("add-meal-time", "");
        openModal("modal-add-meal");
    });
    document.getElementById("close-add-meal")?.addEventListener("click", () => {
        closeModal("modal-add-meal");
    });
    document.getElementById("save-add-meal")?.addEventListener("click", async () => {
        const category = getInputValue("add-meal-category").trim();
        if (!category) {
            return;
        }
        await NutritionAPI.createMeal({
            name: category,
            category: getInputValue("add-meal-category"),
            time: getInputValue("add-meal-time") || null,
        });
        closeModal("modal-add-meal");
        await onRefresh();
    });
    document.getElementById("close-edit-meal")?.addEventListener("click", () => {
        closeModal("modal-edit-meal");
    });
    document.getElementById("save-edit-meal")?.addEventListener("click", async () => {
        const id = getInputValue("edit-meal-id");
        const category = getInputValue("edit-meal-category").trim();
        if (!id || !category) {
            return;
        }
        await NutritionAPI.updateMeal(Number(id), {
            name: category,
            category: getInputValue("edit-meal-category"),
            time: getInputValue("edit-meal-time") || null,
        });
        closeModal("modal-edit-meal");
        await onRefresh();
    });
}
