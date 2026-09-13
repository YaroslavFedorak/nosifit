import { openExerciseModal } from "../exercise.js";
import { TrainingAPI } from "../../widgets/training/api.js";
import { DAYS } from "./constants.js";
import { dom } from "./dom.js";
import {
    addExercise,
    setPlan,
    state,
    Plan
} from "./state.js";
import { savePlan } from "./services/save.js";
import { renderExercises } from "./ui/render.js";

type PlanSavedCallback =
    ((savedPlan: any) => void | Promise<void>)
    | null;

type ExercisePickerCallback =
    ((exercise: any) => void)
    | null;

let initialized = false;

let onPlanSaved: PlanSavedCallback =
    null;

let openRequestId = 0;

function openExercisePicker(
    callback: ExercisePickerCallback
): void {
    openExerciseModal(
        callback
    );
}

function renderDays(): void {
    if (!dom.days) {
        return;
    }

    dom.days.innerHTML = "";

    DAYS.forEach(day => {
        const button =
            document.createElement(
                "button"
            );

        button.type = "button";

        button.className =
            "db-plan-day";

        button.dataset.day =
            day.key;

        button.innerHTML =
            `<span>${day.short}</span><span class="db-plan-day-badge" data-day-badge="${day.key}"></span>`;

        button.classList.toggle(
            "active",
            day.key ===
                state.currentDay
        );

        button.addEventListener(
            "click",
            () => {
                state.currentDay =
                    day.key;

                renderDays();

                renderExercises(
                    openExercisePicker
                );
            }
        );

        dom.days?.appendChild(
            button
        );
    });
}

function openModal(): void {
    dom.modal?.classList.add(
        "open"
    );

    dom.modal?.setAttribute(
        "aria-hidden",
        "false"
    );

    document.body.classList.add(
        "db-modal-open"
    );
}

export function closePlanModal(): void {
    dom.modal?.classList.remove(
        "open"
    );

    dom.modal?.setAttribute(
        "aria-hidden",
        "true"
    );

    document.body.classList.remove(
        "db-modal-open"
    );
}

async function resolvePlan(
    plan: Plan | null
): Promise<Plan | null> {
    if (
        plan?.id ||
        plan?.days
    ) {
        return plan;
    }

    const plans =
        await TrainingAPI.getPlans();

    return (
        plans.find(
            (item: any) =>
                item.is_active
        ) ?? null
    );
}

export async function openPlanModal(
    plan: Plan | null = null,
    onSaved: PlanSavedCallback = null
): Promise<void> {
    const requestId =
        ++openRequestId;

    let resolvedPlan:
        Plan | null = plan;

    try {
        resolvedPlan =
            await resolvePlan(
                plan
            );
    } catch (error) {
        console.error(
            "Failed to load training plans:",
            error
        );
    }

    if (
        requestId !==
        openRequestId
    ) {
        return;
    }

    setPlan(
        resolvedPlan
    );

    onPlanSaved =
        typeof onSaved ===
        "function"
            ? onSaved
            : null;

    if (dom.titleInput) {
        dom.titleInput.value =
            resolvedPlan?.name ??
            "Мій план";
    }

    renderDays();

    renderExercises(
        openExercisePicker
    );

    openModal();
}

export function initPlanModal(): void {
    if (
        initialized ||
        !dom.modal
    ) {
        return;
    }

    initialized = true;

    dom.addExerciseButton
        ?.addEventListener(
            "click",
            () => {
                openExercisePicker(
                    exercise => {
                        addExercise(
                            exercise
                        );

                        renderDays();

                        renderExercises(
                            openExercisePicker
                        );
                    }
                );
            }
        );

    dom.emptyAddExerciseButton
        ?.addEventListener(
            "click",
            () => {
                dom.addExerciseButton
                    ?.click();
            }
        );

    dom.helpToggle
        ?.addEventListener(
            "click",
            () => {
                const isOpen =
                    dom.helpPopover
                        ?.classList.toggle(
                            "open"
                        ) ?? false;

                dom.helpToggle?.setAttribute(
                    "aria-expanded",
                    String(isOpen)
                );
            }
        );

    dom.saveButton
        ?.addEventListener(
            "click",
            async () => {
                try {
                    const savedPlan =
                        await savePlan();

                    await onPlanSaved?.(
                        savedPlan
                    );

                    closePlanModal();
                } catch (error) {
                    console.error(
                        "Failed to save training plan:",
                        error
                    );
                }
            }
        );

    dom.closeButtons.forEach(
        button => {
            button.addEventListener(
                "click",
                closePlanModal
            );
        }
    );

    dom.modal.addEventListener(
        "click",
        event => {
            if (
                event.target ===
                dom.modal
            ) {
                closePlanModal();
            }
        }
    );
}