import { TrainingAPI } from "../../../widgets/training/api.js";
import { dashboard_t } from "../../../../i18n/index.js";
import { dom } from "../dom.js";
import {
    normalizeDays,
    state
} from "../state.js";
import { showToast } from "../ui/toast.js";

function setSaving(
    isSaving: boolean
): void {
    const text =
        dom.saveButton?.querySelector(
            ".btn-text"
        );

    const loader =
        dom.saveButton?.querySelector(
            ".btn-loader"
        );

    if (dom.saveButton) {
        dom.saveButton.disabled =
            isSaving;
    }

    text?.classList.toggle(
        "hidden",
        isSaving
    );

    loader?.classList.toggle(
        "hidden",
        !isSaving
    );
}

export async function savePlan(): Promise<any> {
    const payload = {
        name:
            dom.titleInput?.value.trim() ||
            dashboard_t(
                "plan.defaultTitle"
            ),
        is_active: true,
        days: state.days
    };

    setSaving(true);

    try {
        const savedPlan =
            state.planId
                ? await TrainingAPI.updatePlan(
                    state.planId,
                    payload
                )
                : await TrainingAPI.savePlan(
                    payload
                );

        state.planId =
            savedPlan.id;

        state.days =
            normalizeDays(
                savedPlan.days
            );

        showToast(
            dashboard_t(
                "plan.saveSuccess"
            )
        );

        return savedPlan;
    } catch (error) {
        showToast(
            dashboard_t(
                "plan.saveFailed"
            )
        );

        throw error;
    } finally {
        setSaving(false);
    }
}
