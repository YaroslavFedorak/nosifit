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
    document.getElementById("open-water-modal")?.addEventListener("click", () => {
        setInputValue("water-amount", "");
        openModal("modal-water");
    });
    document.getElementById("close-water-modal")?.addEventListener("click", () => {
        closeModal("modal-water");
    });
    document.getElementById("save-water")?.addEventListener("click", async () => {
        const amount = Number(getInputValue("water-amount") || 0);
        if (!amount || amount <= 0) {
            return;
        }
        await NutritionAPI.addWater(amount);
        closeModal("modal-water");
        await onRefresh();
    });
}
