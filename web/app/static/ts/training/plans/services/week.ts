import {
    ApiError,
    TrainingAPI
} from "../../api.js";

import {
    trainingStore
} from "../../store.js";

import {
    state
} from "../state.js";

import {
    t
} from "../../../i18n/index.js";

import {
    showToast
} from "../ui/toast.js";

import {
    savePlan
} from "./save.js";

// Completion state of the saved plan for the current week.
export async function loadWeek(): Promise<void> {
    const id =
        trainingStore.plan?.id;

    if (!id) {
        state.week = null;

        return;
    }

    try {
        state.week =
            await TrainingAPI.getPlanWeek(id);
    } catch {
        state.week = null;
    }
}

// Saves first, so the day that is recorded is the one on the screen.
export async function completeCurrentDay(): Promise<boolean> {
    if (
        !(await savePlan({
            close: false,
            quiet: true
        }))
    ) {
        return false;
    }

    const id =
        trainingStore.plan?.id;

    if (!id) {
        return false;
    }

    try {
        await TrainingAPI.completePlanDay(
            id,
            state.currentDay
        );

        await loadWeek();

        showToast(
            t("plan.completed")
        );

        return true;
    } catch (error) {
        showToast(
            error instanceof ApiError &&
            error.code === "day_in_future"
                ? t("plan.futureDay")
                : t("plan.completeError")
        );

        return false;
    }
}
