import { state, normalize, normalizeMeta, serializeDays } from "../state.js";
import { showToast } from "../ui/toast.js";
import { ApiError, TrainingAPI } from "../../api.js";
import { trainingStore } from "../../store.js";
import { dom } from "../dom.js";
import { t } from "../../../i18n/index.js";
export async function savePlan(options = {}) {
    const { close = true, quiet = false } = options;
    const button = dom.saveBtn;
    const titleInput = dom.titleInput;
    if (!button ||
        !titleInput) {
        return false;
    }
    const text = button.querySelector(".btn-text");
    const loader = button.querySelector(".btn-loader");
    const payload = {
        name: titleInput.value ||
            t("plan.name"),
        is_active: true,
        days: serializeDays()
    };
    button.disabled =
        true;
    text?.classList.add("hidden");
    loader?.classList.remove("hidden");
    try {
        const saved = trainingStore.plan?.id
            ? await TrainingAPI.updatePlan(trainingStore.plan.id, payload)
            : await TrainingAPI.savePlan(payload);
        trainingStore.plan =
            saved;
        state.days =
            normalize(saved.days ?? {});
        state.meta =
            normalizeMeta(saved.days);
        if (!quiet) {
            showToast(t("plan.saved"));
        }
        if (close) {
            setTimeout(() => {
                dom.modal?.classList.remove("open");
            }, 600);
        }
        return true;
    }
    catch (error) {
        // The server explains a rejected day (for example equipment that
        // the day does not have); anything else is a generic failure.
        showToast(error instanceof ApiError &&
            error.code === "invalid_input"
            ? error.message
            : t("plan.saveError"));
        return false;
    }
    finally {
        button.disabled =
            false;
        loader?.classList.add("hidden");
        text?.classList.remove("hidden");
    }
}
