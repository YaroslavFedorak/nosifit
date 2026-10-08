import type {
    Exercise,
    PlanExercise
} from "../../api.js";

import {
    createExerciseCard
} from "./exerciseCard.js";

import {
    updateSummary
} from "./summary.js";

import {
    state
} from "../state.js";

type Rerender = () => void;

type OpenPicker = (
    callback: (
        exercise: Exercise
    ) => void
) => void;

export function renderExercises(
    openPicker: OpenPicker
): void {
    const container =
        document.getElementById(
            "tr-plan-exercises"
        );

    const emptyState =
        document.getElementById(
            "tr-plan-empty"
        );

    if (
        !container ||
        !emptyState
    ) {
        return;
    }

    const list =
        state.days[
            state.currentDay
        ];

    container.innerHTML = "";

    if (!list.length) {
        container.classList.add(
            "hidden"
        );

        emptyState.classList.remove(
            "hidden"
        );

        updateSummary();

        return;
    }

    container.classList.remove(
        "hidden"
    );

    emptyState.classList.add(
        "hidden"
    );

    const rerender =
        (): void => {
            renderExercises(
                openPicker
            );
        };

    list.forEach(
        (
            exercise: PlanExercise,
            index: number
        ) => {
            const card =
                createExerciseCard(
                    exercise,
                    index,
                    list,
                    rerender,
                    openPicker
                );

            container.appendChild(
                card
            );
        }
    );

    updateSummary();
}