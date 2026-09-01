import { TrainingAPI } from "../../../../training/api.js";
import { dom } from "../dom.js";
import { normalizeDays, state } from "../state.js";
import { showToast } from "../ui/toast.js";

function setSaving(isSaving) {
    const text = dom.saveButton?.querySelector(".btn-text");
    const loader = dom.saveButton?.querySelector(".btn-loader");

    if (dom.saveButton) dom.saveButton.disabled = isSaving;
    text?.classList.toggle("hidden", isSaving);
    loader?.classList.toggle("hidden", !isSaving);
}

export async function savePlan() {
    const payload = {
        name: dom.titleInput?.value.trim() || "Мій план",
        is_active: true,
        days: state.days
    };

    setSaving(true);

    try {
        const savedPlan = state.planId
            ? await TrainingAPI.updatePlan(state.planId, payload)
            : await TrainingAPI.savePlan(payload);

        state.planId = savedPlan.id;
        state.days = normalizeDays(savedPlan.days);
        showToast("План збережено");
        return savedPlan;
    } catch (error) {
        showToast("Не вдалося зберегти план");
        throw error;
    } finally {
        setSaving(false);
    }
}
