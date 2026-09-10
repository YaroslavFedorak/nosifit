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
export function setupWaterModal(onRefresh) {
    document.getElementById("add-water")?.addEventListener("click", () => {
        setInputValue("water-amount", "");
        openModal("modal-water");
    });
    document.getElementById("close-water-modal")?.addEventListener("click", () => {
        closeModal("modal-water");
    });
    document.getElementById("save-water")?.addEventListener("click", async () => {
        const amount = Number(getInputValue("water-amount"));
        if (!Number.isFinite(amount) ||
            amount <= 0) {
            return;
        }
        const saveButton = document.getElementById("save-water");
        if (saveButton) {
            saveButton.disabled = true;
        }
        try {
            await NutritionAPI.addWater(amount);
            closeModal("modal-water");
            document.dispatchEvent(new CustomEvent("nutrition:water-updated"));
            await onRefresh();
        }
        catch (error) {
            console.error("Failed to save water:", error);
        }
        finally {
            if (saveButton) {
                saveButton.disabled = false;
            }
        }
    });
}
