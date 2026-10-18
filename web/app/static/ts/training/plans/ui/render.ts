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

import {
    allowedEquipment,
    missingEquipment
} from "../availability.js";

import {
    t
} from "../../../i18n/index.js";

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

    const allowed =
        allowedEquipment(
            state.meta[
                state.currentDay
            ]
        );

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

            // The server refuses to save a day that holds exercises its
            // equipment cannot do; say which ones before it comes to that.
            const missing =
                missingEquipment(
                    exercise.exercise,
                    allowed
                );

            if (missing.length) {
                card.classList.add(
                    "unavailable"
                );

                const hint =
                    document.createElement(
                        "div"
                    );

                hint.className =
                    "tr-plan-card-warn";

                hint.setAttribute(
                    "role",
                    "alert"
                );

                hint.textContent =
                    t(
                        "plan.needs",
                        {
                            equipment:
                                missing
                                    .map(
                                        slug =>
                                            t(
                                                `plan.equipmentNames.${slug}`
                                            )
                                    )
                                    .join(", ")
                        }
                    );

                card.appendChild(
                    hint
                );
            }

            container.appendChild(
                card
            );
        }
    );

    updateSummary();
}