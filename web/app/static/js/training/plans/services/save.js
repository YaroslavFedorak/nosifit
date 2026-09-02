import { state, normalize } from "../state.js";
import { showToast } from "../ui/toast.js";
import { TrainingAPI } from "../../api.js";
import { dom } from "../dom.js";

export async function savePlan() {
    const btn = dom.saveBtn;
    const text = btn.querySelector(".btn-text");
    const loader = btn.querySelector(".btn-loader");

    const payload = {
        name: dom.titleInput.value || "Мій план",
        is_active: true,
        days: state.days
    };

    btn.disabled = true;
    text?.classList.add("hidden");
    loader?.classList.remove("hidden");

    try {
        const saved = window.trainingStore.plan?.id
            ? await TrainingAPI.updatePlan(window.trainingStore.plan.id, payload)
            : await TrainingAPI.savePlan(payload);

        window.trainingStore.plan = saved;

        const normalized = normalize(saved.days || {});
        Object.keys(normalized).forEach(day => {
            state.days[day] = normalized[day];
        });

        showToast("План збережено");
        setTimeout(() => dom.modal.classList.remove("open"), 600);
    } catch {
        showToast("Помилка збереження");
    } finally {
        btn.disabled = false;
        loader?.classList.add("hidden");
        text?.classList.remove("hidden");
    }
}
