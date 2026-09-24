import {
    state,
    normalize
} from "../state.js";

import {
    showToast
} from "../ui/toast.js";

import {
    TrainingAPI
} from "../../api.js";

import {
    trainingStore
} from "../../store.js";

import {
    dom
} from "../dom.js";

import {
    t
} from "../../../i18n/index.js";

export async function savePlan(): Promise<void> {
    const button =
        dom.saveBtn;

    const titleInput =
        dom.titleInput;

    if (
        !button ||
        !titleInput
    ) {
        return;
    }

    const text =
        button.querySelector<HTMLElement>(
            ".btn-text"
        );

    const loader =
        button.querySelector<HTMLElement>(
            ".btn-loader"
        );

    const payload = {
        name:
            titleInput.value ||
            t("plan.name"),

        is_active:
            true,

        days:
            state.days
    };

    button.disabled =
        true;

    text?.classList.add(
        "hidden"
    );

    loader?.classList.remove(
        "hidden"
    );

    try {
        const saved =
            trainingStore.plan?.id
                ? await TrainingAPI.updatePlan(
                    trainingStore.plan.id,
                    payload
                )
                : await TrainingAPI.savePlan(
                    payload
                );

        trainingStore.plan =
            saved;

        const normalized =
            normalize(
                saved.days ?? {}
            );

        state.days =
            normalized;

        showToast(
            t("plan.saved")
        );

        setTimeout(
            () => {
                dom.modal?.classList.remove(
                    "open"
                );
            },
            600
        );
    } catch {
        showToast(
            t("plan.saveError")
        );
    } finally {
        button.disabled =
            false;

        loader?.classList.add(
            "hidden"
        );

        text?.classList.remove(
            "hidden"
        );
    }
}