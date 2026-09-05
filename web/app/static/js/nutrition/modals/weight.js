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
export function setupWeightModal(onRefresh) {
    document.getElementById("open-update-weight")?.addEventListener("click", () => {
        setInputValue("update-weight-value", "");
        openModal("modal-update-weight");
    });
    document.getElementById("close-update-weight")?.addEventListener("click", () => {
        closeModal("modal-update-weight");
    });
    document.getElementById("save-update-weight")?.addEventListener("click", async () => {
        const weight = Number(getInputValue("update-weight-value"));
        if (!weight || weight <= 0) {
            return;
        }
        await NutritionAPI.updateWeight(weight);
        closeModal("modal-update-weight");
        await onRefresh();
    });
}
